from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re
from typing import Annotated
from urllib.parse import unquote
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import ManageMatchReportUser
from app.core.config import settings
from app.db.session import get_db
from app.models.match import Match
from app.models.event import Event
from app.models.event_player_assignment_audit import EventPlayerAssignmentAudit
from app.models.player import Player
from app.models.match_report import (
    MatchReportImport,
    OfficialPlayerMatchStat,
    OfficialTeamMatchStat,
)
from app.models.team import Team
from app.repositories import match as matches
from app.repositories import match_report as reports
from app.schemas.match_report import (
    MatchReportConfirm,
    MatchReportPreview,
    MatchReportRead,
    OfficialPlayerStatRead,
    OfficialTeamStatRead,
    ParsedMatchReport,
)
from app.services.match_report_parser import (
    PARSER_NAME,
    MatchReportParseError,
    parse_official_match_report_pdf,
)


router = APIRouter(tags=["match-reports"])
DatabaseSession = Annotated[Session, Depends(get_db)]
REPORT_TEAM_ALIASES: dict[str, set[str]] = {
    "GER": {"germany", "deutschland", "德国"},
    "DEN": {"denmark", "danmark", "丹麦"},
}


def _link_unassigned_verified_goals(
    db: Session,
    *,
    match_id: int,
    side_mapping: dict[str, tuple[int, dict]],
    players_by_team_number: dict[tuple[int, int], Player],
    user_id: int,
    user_name: str,
) -> int:
    aliases_by_team: dict[int, set[str]] = {}
    for team_id, report_team in side_mapping.values():
        team = db.get(Team, team_id)
        aliases = {
            report_team["name"],
            report_team["code"],
            *REPORT_TEAM_ALIASES.get(report_team["code"].upper(), set()),
        }
        if team is not None:
            aliases.update({team.name, team.short_name, team.country})
        aliases_by_team[team_id] = {
            _normalize(alias) for alias in aliases if _normalize(alias)
        }

    linked_count = 0
    unassigned_goals = db.scalars(
        select(Event).where(
            Event.match_id == match_id,
            Event.event_type == "goal",
            Event.status == "verified",
            Event.player_id.is_(None),
            Event.deleted_at.is_(None),
        )
    )
    for event in unassigned_goals:
        normalized_note = _normalize(event.note or "")
        number_match = re.search(r"(?:#\s*)?(\d{1,2})(?:\s*号)?", event.note or "")
        if number_match is None:
            continue
        note_team_id = next(
            (
                team_id
                for team_id, aliases in aliases_by_team.items()
                if any(alias in normalized_note for alias in aliases)
            ),
            None,
        )
        team_id = note_team_id or event.team_id
        if team_id is None:
            continue
        player = players_by_team_number.get((team_id, int(number_match.group(1))))
        if player is None:
            continue
        event.player_id = player.id
        event.team_id = team_id
        event.updated_by_user_id = user_id
        db.add(
            EventPlayerAssignmentAudit(
                match_id=match_id,
                event_id=event.id,
                old_player_id=None,
                old_player_name=None,
                new_player_id=player.id,
                new_player_name=player.name,
                changed_by_user_id=user_id,
                changed_by_user_name=user_name,
            )
        )
        linked_count += 1
    return linked_count


def _read_filename(raw_filename: str | None) -> str:
    filename = Path(unquote(raw_filename or "")).name.strip()
    if not filename:
        raise HTTPException(status_code=422, detail="请选择 PDF 赛后统计表。")
    if len(filename) > 255:
        raise HTTPException(status_code=422, detail="文件名过长。")
    if Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=415, detail="当前只支持 PDF 赛后统计表。")
    return filename


def _normalize(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.casefold(), flags=re.UNICODE)


def _team_matches_report(team: Team, report_team: dict) -> bool:
    candidates = {_normalize(team.name), _normalize(team.short_name), _normalize(team.country)}
    aliases = REPORT_TEAM_ALIASES.get(report_team["code"].upper(), set())
    report_values = {
        _normalize(report_team["name"]),
        _normalize(report_team["code"]),
        *{_normalize(alias) for alias in aliases},
    }
    return bool({value for value in candidates if value} & {value for value in report_values if value})


def _suggest_mapping(
    match: Match, home_team: Team, away_team: Team, parsed: dict
) -> tuple[int, int, list[str]]:
    a_home = _team_matches_report(home_team, parsed["team_a"])
    a_away = _team_matches_report(away_team, parsed["team_a"])
    b_home = _team_matches_report(home_team, parsed["team_b"])
    b_away = _team_matches_report(away_team, parsed["team_b"])
    conflicts: list[str] = []
    if a_home and b_away:
        team_a_id, team_b_id = match.home_team_id, match.away_team_id
    elif a_away and b_home:
        team_a_id, team_b_id = match.away_team_id, match.home_team_id
    else:
        team_a_id, team_b_id = match.home_team_id, match.away_team_id
        conflicts.append("无法根据队名自动确认双方映射，请人工检查 Team A 和 Team B。")

    report_date = parsed.get("match_date")
    if report_date:
        try:
            parsed_date = datetime.strptime(report_date, "%d %b %Y").date()
            if parsed_date != match.match_date:
                conflicts.append(
                    f"报告日期 {parsed_date.isoformat()} 与当前比赛日期 {match.match_date.isoformat()} 不一致。"
                )
        except ValueError:
            conflicts.append("报告日期无法标准化，请人工核对。")

    score_by_team = {
        team_a_id: parsed["team_a"]["final_score"],
        team_b_id: parsed["team_b"]["final_score"],
    }
    expected_home = score_by_team[match.home_team_id]
    expected_away = score_by_team[match.away_team_id]
    if match.home_score is not None and (match.home_score, match.away_score) != (
        expected_home,
        expected_away,
    ):
        conflicts.append(
            f"当前比分 {match.home_score}:{match.away_score} 与报告比分 {expected_home}:{expected_away} 不一致。"
        )
    return team_a_id, team_b_id, conflicts


def _preview_response(report: MatchReportImport, *, duplicate: bool) -> MatchReportPreview:
    return MatchReportPreview(
        id=report.id,
        match_id=report.match_id,
        original_filename=report.original_filename,
        status=report.status,
        parsed=ParsedMatchReport.model_validate(report.parsed_data),
        conflicts=list(report.conflicts or []),
        suggested_team_a_team_id=report.team_a_team_id,
        suggested_team_b_team_id=report.team_b_team_id,
        duplicate=duplicate,
        created_at=report.created_at,
    )


def _read_response(db: Session, report: MatchReportImport) -> MatchReportRead:
    return MatchReportRead(
        id=report.id,
        match_id=report.match_id,
        original_filename=report.original_filename,
        status=report.status,
        parsed=ParsedMatchReport.model_validate(report.parsed_data),
        conflicts=list(report.conflicts or []),
        team_a_team_id=report.team_a_team_id,
        team_b_team_id=report.team_b_team_id,
        player_stats=[
            OfficialPlayerStatRead.model_validate(record)
            for record in reports.list_player_stats(db, report.id)
        ],
        team_stats=[
            OfficialTeamStatRead.model_validate(record)
            for record in reports.list_team_stats(db, report.id)
        ],
        imported_at=report.imported_at,
        created_at=report.created_at,
    )


@router.post(
    "/api/matches/{match_id}/official-reports/preview",
    response_model=MatchReportPreview,
)
async def preview_match_report(
    match_id: int,
    request: Request,
    db: DatabaseSession,
    current_user: ManageMatchReportUser,
    x_original_filename: Annotated[str | None, Header()] = None,
) -> MatchReportPreview:
    match = matches.get_match(db, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    filename = _read_filename(x_original_filename)
    content_type = request.headers.get("content-type", "").split(";", maxsplit=1)[0].lower()
    if content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="当前只支持 PDF 赛后统计表。")
    content = await request.body()
    if not content:
        raise HTTPException(status_code=422, detail="PDF 文件为空。")
    if len(content) > settings.match_report_max_bytes:
        raise HTTPException(status_code=413, detail="PDF 超过允许的文件大小。")

    checksum = sha256(content).hexdigest()
    existing = reports.find_report_by_checksum(db, match_id, checksum)
    if existing is not None:
        home_team = db.get(Team, match.home_team_id)
        away_team = db.get(Team, match.away_team_id)
        if home_team is not None and away_team is not None:
            team_a_id, team_b_id, conflicts = _suggest_mapping(
                match, home_team, away_team, existing.parsed_data
            )
            existing.team_a_team_id = team_a_id
            existing.team_b_team_id = team_b_id
            existing.conflicts = conflicts
            db.commit()
            db.refresh(existing)
        return _preview_response(existing, duplicate=True)

    try:
        parsed = parse_official_match_report_pdf(content)
    except MatchReportParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    home_team = db.get(Team, match.home_team_id)
    away_team = db.get(Team, match.away_team_id)
    if home_team is None or away_team is None:
        raise HTTPException(status_code=409, detail="比赛关联球队不存在，无法导入。")
    team_a_id, team_b_id, conflicts = _suggest_mapping(match, home_team, away_team, parsed)

    report_id = str(uuid4())
    storage_dir = settings.match_report_storage_path / str(match_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / f"{report_id}.pdf"
    storage_path.write_bytes(content)
    report = MatchReportImport(
        id=report_id,
        match_id=match_id,
        uploaded_by_user_id=current_user.id,
        original_filename=filename,
        storage_key=str(storage_path.relative_to(settings.match_report_storage_path)),
        content_type="application/pdf",
        size_bytes=len(content),
        checksum_sha256=checksum,
        parser_name=PARSER_NAME,
        parsed_data=parsed,
        conflicts=conflicts,
        team_a_team_id=team_a_id,
        team_b_team_id=team_b_id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _preview_response(report, duplicate=False)


@router.post(
    "/api/matches/{match_id}/official-reports/{report_id}/confirm",
    response_model=MatchReportRead,
)
def confirm_match_report(
    match_id: int,
    report_id: str,
    payload: MatchReportConfirm,
    db: DatabaseSession,
    current_user: ManageMatchReportUser,
) -> MatchReportRead:
    match = matches.get_match(db, match_id)
    report = reports.get_report(db, report_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    if report is None or report.match_id != match_id:
        raise HTTPException(status_code=404, detail="Official report preview not found")
    if report.conflicts and not payload.accept_conflicts:
        raise HTTPException(status_code=409, detail="存在待确认冲突，请确认后再导入。")
    participant_ids = {match.home_team_id, match.away_team_id}
    if {payload.team_a_team_id, payload.team_b_team_id} != participant_ids:
        raise HTTPException(status_code=422, detail="报告双方必须映射到当前比赛的两支参赛球队。")

    parsed = report.parsed_data
    side_mapping = {
        "A": (payload.team_a_team_id, parsed["team_a"]),
        "B": (payload.team_b_team_id, parsed["team_b"]),
    }
    # The confirmed official report is authoritative: Team A becomes the left/home
    # side and Team B becomes the right/away side everywhere on the match page.
    match.home_team_id = payload.team_a_team_id
    match.away_team_id = payload.team_b_team_id
    match.home_score = parsed["team_a"]["final_score"]
    match.away_score = parsed["team_b"]["final_score"]
    match.status = "completed"
    if parsed.get("match_date"):
        match.match_date = datetime.strptime(parsed["match_date"], "%d %b %Y").date()
    if parsed.get("start_time"):
        match.start_time = datetime.strptime(parsed["start_time"], "%H:%M").time()
    if parsed.get("competition_stage"):
        match.stage = parsed["competition_stage"][:80]

    if report.status == "imported":
        db.execute(
            delete(OfficialPlayerMatchStat).where(
                OfficialPlayerMatchStat.report_import_id == report.id
            )
        )
        db.execute(
            delete(OfficialTeamMatchStat).where(
                OfficialTeamMatchStat.report_import_id == report.id
            )
        )

    players_by_team_number = {}
    for side, (team_id, team_data) in side_mapping.items():
        db.add(
            OfficialTeamMatchStat(
                report_import_id=report.id,
                match_id=match_id,
                team_id=team_id,
                report_side=side,
                half_time_score=team_data["half_time_score"],
                final_score=team_data["final_score"],
                seven_meter_goals=team_data["seven_meter_goals"],
                seven_meter_attempts=team_data["seven_meter_attempts"],
                timeouts=team_data["timeouts"],
            )
        )
        for player_data in team_data["players"]:
            player = reports.find_or_create_report_player(
                db,
                team_id=team_id,
                number=player_data["number"],
                name=player_data["name"],
            )
            players_by_team_number[(team_id, player_data["number"])] = player
            db.add(
                OfficialPlayerMatchStat(
                    report_import_id=report.id,
                    match_id=match_id,
                    team_id=team_id,
                    player_id=player.id,
                    player_name=player_data["name"],
                    number=player_data["number"],
                    goals=player_data["goals"],
                    yellow_cards=player_data["yellow_cards"],
                    suspensions_2min=player_data["suspensions_2min"],
                    red_cards=player_data["red_cards"],
                    blue_cards=player_data["blue_cards"],
                )
            )

    db.flush()
    _link_unassigned_verified_goals(
        db,
        match_id=match_id,
        side_mapping=side_mapping,
        players_by_team_number=players_by_team_number,
        user_id=current_user.id,
        user_name=current_user.display_name,
    )

    report.team_a_team_id = payload.team_a_team_id
    report.team_b_team_id = payload.team_b_team_id
    report.status = "imported"
    report.imported_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return _read_response(db, report)


@router.get(
    "/api/matches/{match_id}/official-reports/latest",
    response_model=MatchReportRead | None,
)
def get_latest_match_report(match_id: int, db: DatabaseSession) -> MatchReportRead | None:
    if matches.get_match(db, match_id) is None:
        raise HTTPException(status_code=404, detail="Match not found")
    report = reports.latest_imported_report(db, match_id)
    return _read_response(db, report) if report else None
