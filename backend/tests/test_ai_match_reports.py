import json

from fastapi.testclient import TestClient

from app.api.routes import ai_match_reports as ai_report_routes
from app.core.config import settings
from app.models.ai_match_report import AiMatchReport
from app.schemas.ai_match_report import AiReportContent
from tests.conftest import TestingSessionLocal
from tests.test_matches import setup_references


def create_completed_match(client: TestClient) -> int:
    competition_id, home_id, away_id, venue_id = setup_references(client)
    response = client.post(
        "/api/matches",
        json={
            "competition_id": competition_id,
            "home_team_id": home_id,
            "away_team_id": away_id,
            "venue_id": venue_id,
            "match_date": "2026-10-01",
            "start_time": "19:30",
            "stage": "决赛",
            "status": "completed",
            "home_score": 31,
            "away_score": 29,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_evidence_preview_reports_missing_sources_without_inventing_facts(
    client: TestClient,
) -> None:
    match_id = create_completed_match(client)

    response = client.get(f"/api/matches/{match_id}/ai-reports/evidence")

    assert response.status_code == 200
    body = response.json()
    score_evidence = next(item for item in body["evidence"] if item["id"] == "match.final_score")
    assert "31:29" in score_evidence["value"]
    assert body["limitations"] == [
        "尚未导入已确认的官方赛后统计表。",
        "尚无已确认的视频事件，无法描述比赛进程和关键时间点。",
    ]


def test_generated_report_saves_model_prompt_snapshot_and_evidence(
    client: TestClient,
    monkeypatch,
) -> None:
    match_id = create_completed_match(client)
    monkeypatch.setattr(settings, "match_report_llm_model", "test-report-model")
    monkeypatch.setattr(settings, "match_report_prompt_version", "match-report-v1-test")

    def fake_generate(
        snapshot: dict,
        *,
        valid_evidence_ids: set[str],
        focus: str,
        detail_level: str,
    ):
        assert valid_evidence_ids == {"match.metadata", "match.final_score"}
        assert snapshot["match"]["home_score"] == 31
        assert focus == "team_comparison"
        assert detail_level == "detailed"
        content = AiReportContent(
            title="决赛赛后报告",
            summary="主队以 31:29 完成比赛。",
            sections=[
                {
                    "heading": "比赛结果",
                    "body": "最终比分为 31:29。",
                    "evidence_ids": ["match.final_score"],
                }
            ],
            limitations=list(snapshot["limitations"]),
        )
        return content, json.dumps(content.model_dump(), ensure_ascii=False)

    monkeypatch.setattr(ai_report_routes, "generate_report", fake_generate)

    created = client.post(
        f"/api/matches/{match_id}/ai-reports",
        json={"focus": "team_comparison", "detail_level": "detailed"},
    )
    latest = client.get(f"/api/matches/{match_id}/ai-reports/latest")

    assert created.status_code == 201
    assert created.json()["model_name"] == "test-report-model"
    assert created.json()["prompt_version"] == "match-report-v1-test"
    assert created.json()["generation_focus"] == "team_comparison"
    assert created.json()["detail_level"] == "detailed"
    assert created.json()["report"]["sections"][0]["evidence_ids"] == [
        "match.final_score"
    ]
    assert latest.status_code == 200
    assert latest.json()["id"] == created.json()["id"]
    with TestingSessionLocal() as db:
        stored = db.get(AiMatchReport, created.json()["id"])
        assert stored is not None
        assert stored.input_snapshot["match"]["away_score"] == 29
        assert {item["id"] for item in stored.evidence} == {
            "match.metadata",
            "match.final_score",
        }


def test_generation_explains_model_configuration_is_missing(
    client: TestClient,
    monkeypatch,
) -> None:
    match_id = create_completed_match(client)
    monkeypatch.setattr(settings, "match_report_llm_base_url", "")
    monkeypatch.setattr(settings, "match_report_llm_api_key", "")
    monkeypatch.setattr(settings, "match_report_llm_model", "")

    response = client.post(
        f"/api/matches/{match_id}/ai-reports",
        json={"focus": "full_match", "detail_level": "concise"},
    )

    assert response.status_code == 503
    assert "MATCH_REPORT_LLM_BASE_URL" in response.json()["detail"]


def test_user_edits_are_versioned_and_new_generation_does_not_overwrite_them(
    client: TestClient,
    monkeypatch,
) -> None:
    match_id = create_completed_match(client)
    monkeypatch.setattr(settings, "match_report_llm_model", "test-report-model")

    def fake_generate(snapshot: dict, **_kwargs):
        content = AiReportContent(
            title="AI 原始标题",
            summary="主队以 31:29 完成比赛。",
            sections=[
                {
                    "heading": "比赛结果",
                    "body": "最终比分为 31:29。",
                    "evidence_ids": ["match.final_score"],
                }
            ],
        )
        return content, json.dumps(content.model_dump(), ensure_ascii=False)

    monkeypatch.setattr(ai_report_routes, "generate_report", fake_generate)
    first = client.post(
        f"/api/matches/{match_id}/ai-reports",
        json={"focus": "full_match", "detail_level": "concise"},
    ).json()
    edited_content = {
        **first["report"],
        "title": "教练修改后的标题",
    }
    edited = client.patch(
        f"/api/matches/{match_id}/ai-reports/{first['id']}",
        json={"report": edited_content},
    )
    second = client.post(
        f"/api/matches/{match_id}/ai-reports",
        json={"focus": "key_phases", "detail_level": "detailed"},
    )
    versions = client.get(f"/api/matches/{match_id}/ai-reports")

    assert edited.status_code == 200
    assert edited.json()["is_user_edited"] is True
    assert edited.json()["report"]["title"] == "教练修改后的标题"
    assert second.status_code == 201
    assert len(versions.json()) == 2
    retained = next(item for item in versions.json() if item["id"] == first["id"])
    assert retained["report"]["title"] == "教练修改后的标题"


def test_fact_evaluation_detects_unsupported_numbers_and_compares_versions(
    client: TestClient,
    monkeypatch,
) -> None:
    match_id = create_completed_match(client)
    monkeypatch.setattr(settings, "match_report_llm_model", "test-report-model")

    def fake_generate(snapshot: dict, **_kwargs):
        content = AiReportContent(
            title="赛后报告",
            summary="比赛结果已确认。",
            sections=[
                {
                    "heading": "比赛结果",
                    "body": "最终比分为 31:29。",
                    "evidence_ids": ["match.final_score"],
                }
            ],
        )
        return content, json.dumps(content.model_dump(), ensure_ascii=False)

    monkeypatch.setattr(ai_report_routes, "generate_report", fake_generate)
    first = client.post(
        f"/api/matches/{match_id}/ai-reports",
        json={"focus": "full_match", "detail_level": "concise"},
    ).json()
    first_evaluation = client.post(
        f"/api/matches/{match_id}/ai-reports/{first['id']}/evaluations"
    )
    second = client.post(
        f"/api/matches/{match_id}/ai-reports",
        json={"focus": "full_match", "detail_level": "concise"},
    ).json()
    wrong_content = {
        **second["report"],
        "sections": [
            {
                **second["report"]["sections"][0],
                "body": "最终比分为 31:99。",
            }
        ],
    }
    client.patch(
        f"/api/matches/{match_id}/ai-reports/{second['id']}",
        json={"report": wrong_content},
    )
    second_evaluation = client.post(
        f"/api/matches/{match_id}/ai-reports/{second['id']}/evaluations"
    )

    assert first_evaluation.status_code == 201
    assert first_evaluation.json()["passed"] is True
    assert first_evaluation.json()["score"] == 100.0
    assert second_evaluation.status_code == 201
    assert second_evaluation.json()["passed"] is False
    assert second_evaluation.json()["previous_score"] == 100.0
    assert second_evaluation.json()["score_delta"] < 0
    failed = [check for check in second_evaluation.json()["checks"] if not check["passed"]]
    assert any("99" in check["detail"] for check in failed)
