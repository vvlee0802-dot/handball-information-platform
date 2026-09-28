from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.authorization import UserRole
from app.core.security import hash_password
from app.main import app
from app.models.user import User
from app.schemas.knowledge import KnowledgeAnswer, KnowledgeCitation
from app.services.knowledge_document import ExtractedPage, build_chunks
from app.services.knowledge_rag import cosine_similarity
from tests.conftest import TestingSessionLocal


def test_upload_text_creates_source_chunks_and_delete_removes_file(
    client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "knowledge_document_dir", tmp_path)
    content = (
        "进攻原则\n\n保持场地宽度，利用交叉跑位创造空当。\n\n"
        "防守原则\n\n防守队员需要及时沟通并完成换防。"
    ).encode()
    response = client.post(
        "/api/knowledge/documents",
        content=content,
        headers={
            "Content-Type": "text/plain",
            "X-Original-Filename": "tactics.txt",
            "X-Knowledge-Visibility": "owner_private",
        },
    )
    assert response.status_code == 201
    document = response.json()
    assert document["status"] == "ready"
    assert document["visibility"] == "owner_private"
    assert document["chunk_count"] >= 1
    assert document["chunks"][0]["section_title"] == "进攻原则"
    assert document["chunks"][0]["page_number"] is None
    stored_files = list(tmp_path.iterdir())
    assert len(stored_files) == 1

    listed = client.get("/api/knowledge/documents")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == document["id"]
    assert "chunks" not in listed.json()[0]

    deleted = client.delete(f"/api/knowledge/documents/{document['id']}")
    assert deleted.status_code == 204
    assert not stored_files[0].exists()
    assert client.get(f"/api/knowledge/documents/{document['id']}").status_code == 404


def test_failed_pdf_is_persisted_and_can_be_retried(
    client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "knowledge_document_dir", tmp_path)
    response = client.post(
        "/api/knowledge/documents",
        content=b"%PDF-broken",
        headers={
            "Content-Type": "application/pdf",
            "X-Original-Filename": "rules.pdf",
        },
    )
    assert response.status_code == 201
    failed = response.json()
    assert failed["status"] == "failed"
    assert failed["error_message"]
    assert failed["chunk_count"] == 0

    monkeypatch.setattr(
        "app.api.routes.knowledge.extract_document_pages",
        lambda *_args, **_kwargs: [
            ExtractedPage("规则第一章\n\n一次进攻必须遵守比赛规则。", 1, "规则第一章")
        ],
    )
    retried = client.post(f"/api/knowledge/documents/{failed['id']}/retry")
    assert retried.status_code == 200
    ready = retried.json()
    assert ready["status"] == "ready"
    assert ready["page_count"] == 1
    assert ready["chunk_count"] == 1
    assert ready["error_message"] is None


def test_chunking_retains_page_and_section_sources() -> None:
    chunks = build_chunks(
        [
            ExtractedPage("第一章\n\n规则内容", 1, "第一章"),
            ExtractedPage("第二章\n\n更多规则", 2, "第二章"),
        ]
    )
    assert [chunk["page_number"] for chunk in chunks] == [1, 2]
    assert [chunk["section_title"] for chunk in chunks] == ["第一章", "第二章"]


def test_knowledge_endpoints_require_authentication(anonymous_client: TestClient) -> None:
    response = anonymous_client.get("/api/knowledge/documents")
    assert response.status_code == 401


def test_question_retrieves_chunks_and_returns_traceable_citation(
    client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "knowledge_document_dir", tmp_path)
    uploaded = client.post(
        "/api/knowledge/documents",
        content="七米球规则\n\n当防守行为破坏明显得分机会时，可以判罚七米球。".encode(),
        headers={
            "Content-Type": "text/plain",
            "X-Original-Filename": "rules.txt",
        },
    ).json()
    chunk_id = uploaded["chunks"][0]["id"]
    monkeypatch.setattr(
        "app.services.knowledge_rag.embed_texts",
        lambda texts: [[1.0, 0.0] for _text in texts],
    )
    monkeypatch.setattr(
        "app.api.routes.knowledge_qa.embed_texts",
        lambda texts: [[1.0, 0.0] for _text in texts],
    )
    monkeypatch.setattr(settings, "knowledge_relevance_threshold", 0.3)

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"answer":"破坏明显得分机会时可判罚七米球。",'
                                f'"citation_ids":[{chunk_id}],"insufficient_evidence":false}}'
                            )
                        }
                    }
                ]
            }

    monkeypatch.setattr("app.services.knowledge_rag.httpx.post", lambda *_args, **_kwargs: FakeResponse())
    response = client.post("/api/knowledge/ask", json={"question": "什么时候判罚七米球？"})
    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer["insufficient_evidence"] is False
    assert answer["citations"][0]["chunk_id"] == chunk_id
    assert answer["citations"][0]["document_name"] == "rules.txt"
    assert answer["citations"][0]["section_title"] == "七米球规则"


def test_question_without_documents_refuses_to_invent(client: TestClient) -> None:
    response = client.post("/api/knowledge/ask", json={"question": "什么是七米球？"})
    assert response.status_code == 200
    answer = response.json()
    assert answer["insufficient_evidence"] is True
    assert answer["citations"] == []


def test_cosine_similarity_rejects_unrelated_direction() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_team_private_document_is_hidden_from_other_team(
    client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "knowledge_document_dir", tmp_path)
    team_payload = {
        "city": "测试城市",
        "country": "测试国家",
        "gender": "men",
        "description": None,
    }
    team_one = client.post(
        "/api/teams", json={**team_payload, "name": "一队", "short_name": "一队"}
    ).json()
    team_two = client.post(
        "/api/teams", json={**team_payload, "name": "二队", "short_name": "二队"}
    ).json()
    with TestingSessionLocal() as db:
        db.add_all(
            [
                User(
                    email="owner@team.test",
                    display_name="一队教练",
                    password_hash=hash_password("correct-password"),
                    role=UserRole.COACH_ANALYST.value,
                    team_id=team_one["id"],
                ),
                User(
                    email="teammate@team.test",
                    display_name="一队分析员",
                    password_hash=hash_password("correct-password"),
                    role=UserRole.COACH_ANALYST.value,
                    team_id=team_one["id"],
                ),
                User(
                    email="outsider@team.test",
                    display_name="二队教练",
                    password_hash=hash_password("correct-password"),
                    role=UserRole.COACH_ANALYST.value,
                    team_id=team_two["id"],
                ),
            ]
        )
        db.commit()

    with TestClient(app) as owner:
        owner.post(
            "/api/auth/login",
            json={"email": "owner@team.test", "password": "correct-password"},
        )
        upload = owner.post(
            "/api/knowledge/documents",
            content="一队内部防守战术".encode(),
            headers={
                "Content-Type": "text/plain",
                "X-Original-Filename": "team-plan.txt",
                "X-Knowledge-Visibility": "team_private",
                "X-Knowledge-Team-Id": str(team_one["id"]),
            },
        )
        assert upload.status_code == 201
        document_id = upload.json()["id"]
        assert upload.json()["team_id"] == team_one["id"]

    with TestClient(app) as teammate:
        teammate.post(
            "/api/auth/login",
            json={"email": "teammate@team.test", "password": "correct-password"},
        )
        assert teammate.get(f"/api/knowledge/documents/{document_id}").status_code == 200
        assert [item["id"] for item in teammate.get("/api/knowledge/documents").json()] == [
            document_id
        ]

    with TestClient(app) as outsider:
        outsider.post(
            "/api/auth/login",
            json={"email": "outsider@team.test", "password": "correct-password"},
        )
        denied = outsider.get(f"/api/knowledge/documents/{document_id}")
        assert denied.status_code == 403
        assert outsider.get("/api/knowledge/documents").json() == []


def test_fixed_question_evaluation_records_metrics_and_trace(
    client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "knowledge_document_dir", tmp_path)
    document = client.post(
        "/api/knowledge/documents",
        content="七米球规则\n\n破坏明显得分机会时可以判罚七米球。".encode(),
        headers={
            "Content-Type": "text/plain",
            "X-Original-Filename": "rules.txt",
        },
    ).json()
    created_case = client.post(
        "/api/knowledge/evaluation-cases",
        json={
            "question": "什么时候判罚七米球？",
            "expected_document_ids": [document["id"]],
        },
    )
    assert created_case.status_code == 201, created_case.text

    def fake_index(_db, chunks) -> None:
        for chunk in chunks:
            chunk.embedding = [1.0, 0.0]

    monkeypatch.setattr("app.services.knowledge_evaluation.ensure_chunk_embeddings", fake_index)
    monkeypatch.setattr(
        "app.services.knowledge_evaluation.embed_texts",
        lambda texts: [[1.0, 0.0] for _text in texts],
    )

    def fake_answer(_question, ranked_chunks, *, documents) -> KnowledgeAnswer:
        chunk, score = ranked_chunks[0]
        source = documents[chunk.document_id]
        return KnowledgeAnswer(
            answer="破坏明显得分机会时可以判罚七米球。",
            citations=[
                KnowledgeCitation(
                    chunk_id=chunk.id,
                    document_id=source.id,
                    document_name=source.original_filename,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    excerpt=chunk.content,
                    score=score,
                )
            ],
            insufficient_evidence=False,
            answer_model="test-model",
            embedding_model="test-embedding",
            prompt_version="test-v1",
        )

    monkeypatch.setattr("app.services.knowledge_evaluation.answer_with_chunks", fake_answer)
    response = client.post("/api/knowledge/evaluation-runs")
    assert response.status_code == 200, response.text
    run = response.json()
    assert run["case_count"] == 1
    assert run["recall_at_k"] == 1.0
    assert run["citation_hit_rate"] == 1.0
    assert run["ungrounded_answer_rate"] == 0.0
    assert run["details"][0]["retrieved_chunks"][0]["document_id"] == document["id"]
    assert client.get("/api/knowledge/evaluation-runs").json()[0]["id"] == run["id"]
