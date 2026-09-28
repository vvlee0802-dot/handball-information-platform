import json
import re

import httpx
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.event import Event
from app.models.ai_match_report import AiMatchReport
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
from app.repositories import match_report as match_reports
from app.schemas.ai_match_report import (
    AiReportContent,
    AiReportEvaluationCheck,
    ReportDetailLevel,
    ReportEvidence,
    ReportFocus,
)


class MatchReportGenerationError(RuntimeError):
    pass


def build_evidence_bundle(db: Session, match: Match) -> tuple[dict, list[ReportEvidence], list[str]]:
    teams = {
        team.id: team
        for team in db.scalars(
            select(Team).where(Team.id.in_((match.home_team_id, match.away_team_id)))
        )
    }
    home = teams.get(match.home_team_id)
    away = teams.get(match.away_team_id)
    if home is None or away is None:
        raise MatchReportGenerationError("比赛关联的球队数据不完整。")

    evidence: list[ReportEvidence] = []
    limitations: list[str] = []
    evidence.append(
        ReportEvidence(
            id="match.metadata",
            category="match",
            label="比赛基本信息",
            value=(
                f"{match.match_date.isoformat()}，{match.stage}，"
                f"{home.name} vs {away.name}"
            ),
        )
    )
    if match.home_score is not None and match.away_score is not None:
        evidence.append(
            ReportEvidence(
                id="match.final_score",
                category="match",
                label="最终比分",
                value=f"{home.name} {match.home_score}:{match.away_score} {away.name}",
            )
        )
    else:
        limitations.append("尚无已确认的最终比分。")

    report = match_reports.latest_imported_report(db, match.id)
    if report is None:
        limitations.append("尚未导入已确认的官方赛后统计表。")
    else:
        for stat in match_reports.list_team_stats(db, report.id):
            team = teams.get(stat.team_id)
            if team is None:
                continue
            evidence.append(
                ReportEvidence(
                    id=f"official.team.{stat.team_id}",
                    category="official_team_stat",
                    label=f"{team.name} 官方数据",
                    value=(
                        f"半场 {stat.half_time_score}，全场 {stat.final_score}，"
                        f"7米球 {stat.seven_meter_goals}/{stat.seven_meter_attempts}"
                    ),
                )
            )
        for stat in match_reports.list_player_stats(db, report.id):
            team = teams.get(stat.team_id)
            evidence.append(
                ReportEvidence(
                    id=f"official.player.{stat.id}",
                    category="official_player_stat",
                    label=f"#{stat.number} {stat.player_name}",
                    value=f"{team.name if team else '未知球队'}，进球 {stat.goals}",
                )
            )

    players = {
        player.id: player
        for player in db.scalars(
            select(Player).where(Player.team_id.in_((match.home_team_id, match.away_team_id)))
        )
    }
    verified_events = list(
        db.scalars(
            select(Event)
            .where(
                Event.match_id == match.id,
                Event.status == "verified",
                Event.deleted_at.is_(None),
            )
            .order_by(Event.timestamp_seconds, Event.id)
        )
    )
    if not verified_events:
        limitations.append("尚无已确认的视频事件，无法描述比赛进程和关键时间点。")
    for event in verified_events:
        team = teams.get(event.team_id)
        player = players.get(event.player_id)
        actor = player.name if player else (team.name if team else "未指定对象")
        evidence.append(
            ReportEvidence(
                id=f"event.{event.id}",
                category="verified_event",
                label=f"{event.event_type} · {actor}",
                value=event.note or f"{event.timestamp_seconds:.3f} 秒的已确认事件",
                event_id=event.id,
                timestamp_seconds=event.timestamp_seconds,
            )
        )

    snapshot = {
        "match": {
            "id": match.id,
            "date": match.match_date.isoformat(),
            "stage": match.stage,
            "home_team": home.name,
            "away_team": away.name,
            "home_score": match.home_score,
            "away_score": match.away_score,
        },
        "evidence": [item.model_dump() for item in evidence],
        "limitations": limitations,
    }
    return snapshot, evidence, limitations


FOCUS_INSTRUCTIONS: dict[ReportFocus, str] = {
    "full_match": "按全场概览、比分结果和主要表现组织报告。",
    "key_phases": "聚焦已有时间点支持的关键阶段和进球进程。",
    "team_comparison": "聚焦两队官方比分、半场和可追溯的球队数据对比。",
    "player_performance": "聚焦官方球员进球数和已确认的球员事件。",
}
DETAIL_INSTRUCTIONS: dict[ReportDetailLevel, str] = {
    "concise": "使用 2 至 4 个简短段落，每段尽量不超过 180 个中文字。",
    "detailed": "使用 4 至 8 个有层次的段落，说明证据充分的细节和局限。",
}


def generate_report(
    snapshot: dict,
    *,
    valid_evidence_ids: set[str],
    focus: ReportFocus = "full_match",
    detail_level: ReportDetailLevel = "concise",
) -> tuple[AiReportContent, str]:
    if not (
        settings.match_report_llm_base_url
        and settings.match_report_llm_api_key
        and settings.match_report_llm_model
    ):
        raise MatchReportGenerationError(
            "还没有配置赛后报告模型。请先在 .env 设置 MATCH_REPORT_LLM_BASE_URL、"
            "MATCH_REPORT_LLM_API_KEY 和 MATCH_REPORT_LLM_MODEL。"
        )

    system_prompt = (
        "你是手球赛后报告助手。只能使用输入中的 evidence，不得猜测或补全事实。"
        "每个涉及比分、数量、球员或时间点的段落都要在 evidence_ids 中列出依据。"
        "数据不足时必须写入 limitations，不得编造。返回 JSON，字段为 title、summary、"
        "sections（每项含 heading、body、evidence_ids）、limitations。"
        f"报告重点：{FOCUS_INSTRUCTIONS[focus]}"
        f"表达方式：{DETAIL_INSTRUCTIONS[detail_level]}"
    )
    url = f"{settings.match_report_llm_base_url.rstrip('/')}/chat/completions"
    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {settings.match_report_llm_api_key}"},
            json={
                "model": settings.match_report_llm_model,
                "temperature": 0.1,
                "enable_thinking": settings.match_report_llm_enable_thinking,
                "max_tokens": settings.match_report_llm_max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(snapshot, ensure_ascii=False),
                    },
                ],
            },
            timeout=settings.match_report_llm_timeout_seconds,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        content = AiReportContent.model_validate_json(raw)
    except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as exc:
        raise MatchReportGenerationError(f"模型生成失败：{exc}") from exc

    unknown_ids = {
        evidence_id
        for section in content.sections
        for evidence_id in section.evidence_ids
        if evidence_id not in valid_evidence_ids
    }
    if unknown_ids:
        raise MatchReportGenerationError(
            f"模型引用了不存在的证据：{', '.join(sorted(unknown_ids))}"
        )
    required_limitations = snapshot.get("limitations", [])
    content.limitations = list(dict.fromkeys([*content.limitations, *required_limitations]))
    return content, raw


def _number_tokens(text: str) -> set[str]:
    return {
        token.lstrip("0") or "0"
        for token in re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", text)
    }


def _evidence_text(evidence: ReportEvidence) -> str:
    parts = [evidence.label, evidence.value]
    if evidence.timestamp_seconds is not None:
        total_seconds = int(round(evidence.timestamp_seconds))
        parts.extend(
            [
                f"{evidence.timestamp_seconds:g}",
                f"{total_seconds // 60}:{total_seconds % 60:02d}",
            ]
        )
    return " ".join(parts)


def evaluate_report(
    report: AiMatchReport,
    *,
    current_evidence: list[ReportEvidence],
) -> tuple[list[AiReportEvaluationCheck], float, bool]:
    content = AiReportContent.model_validate(report.user_output_data or report.output_data)
    stored_by_id = {
        item.id: item for item in (ReportEvidence.model_validate(row) for row in report.evidence)
    }
    current_by_id = {item.id: item for item in current_evidence}
    checks: list[AiReportEvaluationCheck] = []

    cited_ids = list(
        dict.fromkeys(
            evidence_id
            for section in content.sections
            for evidence_id in section.evidence_ids
        )
    )
    unknown_ids = [item for item in cited_ids if item not in stored_by_id or item not in current_by_id]
    checks.append(
        AiReportEvaluationCheck(
            key="evidence_traceability",
            label="关键事实可追溯",
            passed=not unknown_ids and all(section.evidence_ids for section in content.sections),
            detail=(
                "所有报告段落均引用了可追溯证据。"
                if not unknown_ids and all(section.evidence_ids for section in content.sections)
                else f"存在无证据段落或无效引用：{', '.join(unknown_ids) or '未引用证据的段落'}"
            ),
            evidence_ids=cited_ids,
        )
    )

    stale_ids = []
    for evidence_id in cited_ids:
        stored = stored_by_id.get(evidence_id)
        current = current_by_id.get(evidence_id)
        if stored is None or current is None:
            continue
        if stored.value != current.value or stored.timestamp_seconds != current.timestamp_seconds:
            stale_ids.append(evidence_id)
    checks.append(
        AiReportEvaluationCheck(
            key="database_consistency",
            label="证据与当前数据库一致",
            passed=not stale_ids,
            detail=(
                "所引用证据与当前数据库一致。"
                if not stale_ids
                else f"数据库已变更，需重新生成或编辑：{', '.join(stale_ids)}"
            ),
            evidence_ids=stale_ids,
        )
    )

    for index, section in enumerate(content.sections, start=1):
        report_numbers = _number_tokens(f"{section.heading} {section.body}")
        supported_numbers: set[str] = set()
        for evidence_id in section.evidence_ids:
            evidence = current_by_id.get(evidence_id)
            if evidence is not None:
                supported_numbers.update(_number_tokens(_evidence_text(evidence)))
        unsupported = sorted(report_numbers - supported_numbers)
        checks.append(
            AiReportEvaluationCheck(
                key=f"section_{index}_numbers",
                label=f"第 {index} 段数字与时间点",
                passed=not unsupported,
                detail=(
                    "段落中的数字和时间点均可由引用证据支持。"
                    if not unsupported
                    else f"以下数字无法从本段引用证据追溯：{', '.join(unsupported)}"
                ),
                evidence_ids=section.evidence_ids,
            )
        )

    passed_count = sum(check.passed for check in checks)
    score = round(passed_count / len(checks) * 100, 1) if checks else 0.0
    return checks, score, all(check.passed for check in checks)
