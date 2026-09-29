from datetime import date, time

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.authorization import UserRole
from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models.agent import AgentActionAudit, ChatMessage, ChatSession
from app.models.competition import Competition
from app.models.match import Match
from app.models.team import Team
from app.models.user import User
from app.models.venue import Venue
from tests.conftest import TestingSessionLocal


class FakeResponse:
    def __init__(self, body: dict) -> None:
        self.body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.body


def seed_match() -> Match:
    with TestingSessionLocal() as db:
        competition = Competition(name="测试杯", season="2026", stage="决赛", status="active")
        home = Team(
            name="德国",
            short_name="GER",
            city="柏林",
            country="德国",
            gender="men",
        )
        away = Team(
            name="丹麦",
            short_name="DEN",
            city="哥本哈根",
            country="丹麦",
            gender="men",
        )
        venue = Venue(name="测试馆", city="巴黎", address="测试路 1 号", capacity=10000)
        db.add_all([competition, home, away, venue])
        db.flush()
        match = Match(
            competition_id=competition.id,
            home_team_id=home.id,
            away_team_id=away.id,
            venue_id=venue.id,
            match_date=date(2026, 9, 29),
            start_time=time(20, 0),
            stage="决赛",
            status="completed",
            home_score=26,
            away_score=39,
        )
        db.add(match)
        db.commit()
        db.refresh(match)
        db.expunge(match)
        return match


def tool_response(name: str, arguments: str, call_id: str = "call-1") -> dict:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {"name": name, "arguments": arguments},
                        }
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
    }


def answer_response(content: str) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28},
    }


def configure_fake_model(monkeypatch, bodies: list[dict], captured: list[dict] | None = None) -> None:
    monkeypatch.setattr(settings, "match_report_llm_base_url", "https://model.test/v1")
    monkeypatch.setattr(settings, "match_report_llm_api_key", "test-key")
    monkeypatch.setattr(settings, "match_report_llm_model", "test-agent")
    queue = iter(bodies)

    def fake_post(*_args, **kwargs):
        if captured is not None:
            captured.append(kwargs["json"])
        return FakeResponse(next(queue))

    monkeypatch.setattr("app.services.match_agent.httpx.post", fake_post)


def test_agent_uses_match_tool_and_persists_trace_and_follow_up_context(
    client: TestClient,
    monkeypatch,
) -> None:
    match = seed_match()
    captured: list[dict] = []
    configure_fake_model(
        monkeypatch,
        [
            tool_response("get_match_overview", f'{{"match_id":{match.id}}}'),
            answer_response("根据比赛信息，丹麦以 39:26 战胜德国。"),
            answer_response("你追问的仍是德国与丹麦这场比赛。"),
        ],
        captured,
    )
    created = client.post("/api/agent/sessions", json={"match_id": match.id})
    assert created.status_code == 201, created.text
    session_id = created.json()["session"]["id"]

    first = client.post(
        f"/api/agent/sessions/{session_id}/messages",
        json={"content": "这场比赛谁赢了？"},
    )
    assert first.status_code == 200, first.text
    turn = first.json()
    assert turn["run"]["status"] == "completed"
    assert turn["run"]["tool_calls"][0]["tool_name"] == "get_match_overview"
    assert turn["run"]["tool_calls"][0]["status"] == "completed"
    assert turn["assistant_message"]["sources"][0]["source_type"] == "match"
    assert turn["run"]["token_usage"]["total_tokens"] == 42

    follow_up = client.post(
        f"/api/agent/sessions/{session_id}/messages",
        json={"content": "他们这场的比分再说一遍。"},
    )
    assert follow_up.status_code == 200
    follow_up_messages = captured[-1]["messages"]
    assert any(message.get("content") == "这场比赛谁赢了？" for message in follow_up_messages)
    assert any("39:26" in (message.get("content") or "") for message in follow_up_messages)

    detail = client.get(f"/api/agent/sessions/{session_id}").json()
    assert len(detail["messages"]) == 4
    assert [message["role"] for message in detail["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert len(detail["runs"]) == 2


def test_agent_denies_tool_outside_user_allowlist_and_does_not_fabricate(
    monkeypatch,
) -> None:
    match = seed_match()
    with TestingSessionLocal() as db:
        coach = User(
            email="coach-agent@example.com",
            display_name="教练",
            password_hash=hash_password("correct-password"),
            role=UserRole.COACH_ANALYST.value,
        )
        db.add(coach)
        db.commit()
    configure_fake_model(
        monkeypatch,
        [
            tool_response(
                "propose_update_match_status",
                f'{{"match_id":{match.id},"status":"cancelled"}}',
            ),
            answer_response("当前账号没有修改比赛数据的权限，因此没有执行修改。"),
        ],
    )
    with TestClient(app) as coach_client:
        coach_client.post(
            "/api/auth/login",
            json={"email": "coach-agent@example.com", "password": "correct-password"},
        )
        session_id = coach_client.post(
            "/api/agent/sessions", json={"match_id": match.id}
        ).json()["session"]["id"]
        response = coach_client.post(
            f"/api/agent/sessions/{session_id}/messages",
            json={"content": "取消这场比赛"},
        )
    assert response.status_code == 200, response.text
    call = response.json()["run"]["tool_calls"][0]
    assert call["status"] == "denied"
    assert call["retryable"] is False
    assert "没有修改比赛数据的权限" in call["error_message"]
    with TestingSessionLocal() as db:
        assert db.get(Match, match.id).status == "completed"


def test_agent_write_requires_confirmation_and_creates_audit(
    client: TestClient,
    monkeypatch,
) -> None:
    match = seed_match()
    configure_fake_model(
        monkeypatch,
        [
            tool_response(
                "propose_update_match_status",
                f'{{"match_id":{match.id},"status":"cancelled"}}',
            ),
            answer_response("已经生成待确认计划，确认前不会修改比赛。"),
        ],
    )
    session_id = client.post(
        "/api/agent/sessions", json={"match_id": match.id}
    ).json()["session"]["id"]
    turn = client.post(
        f"/api/agent/sessions/{session_id}/messages",
        json={"content": "把比赛状态改为取消"},
    ).json()
    proposal = turn["run"]["proposals"][0]
    assert proposal["status"] == "pending"
    with TestingSessionLocal() as db:
        assert db.get(Match, match.id).status == "completed"

    confirmed = client.post(f"/api/agent/proposals/{proposal['id']}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "executed"
    with TestingSessionLocal() as db:
        assert db.get(Match, match.id).status == "cancelled"
        assert db.scalar(select(func.count()).select_from(AgentActionAudit)) == 1


def test_deleting_session_removes_messages_and_short_term_memory(
    client: TestClient,
    monkeypatch,
) -> None:
    match = seed_match()
    configure_fake_model(monkeypatch, [answer_response("请告诉我想了解的比赛问题。")])
    session_id = client.post(
        "/api/agent/sessions", json={"match_id": match.id}
    ).json()["session"]["id"]
    client.post(
        f"/api/agent/sessions/{session_id}/messages",
        json={"content": "你好"},
    )
    deleted = client.delete(f"/api/agent/sessions/{session_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/agent/sessions/{session_id}").status_code == 404
    with TestingSessionLocal() as db:
        assert db.get(ChatSession, session_id) is None
        assert db.scalar(select(func.count()).select_from(ChatMessage)) == 0
