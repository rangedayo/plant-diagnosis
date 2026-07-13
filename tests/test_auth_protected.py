"""[인증 통합] /compare·/trend + [배포 비용 가드] /diagnose·/diagnose/refine 보호 검증.

- 토큰 없으면 401 (require_user가 Authorization 헤더를 먼저 보고 거부 → firebase/ADC 불필요).
- require_user override로 인증 통과 시 핸들러에 도달(LLM·토큰 검증 없이 상태코드로 확인).
- 진단 계열은 Gemini·OpenAI 과금 엔드포인트라, 401이 뚫리면 공개 배포에서 비용 악용 가능.
"""

from fastapi.testclient import TestClient

import app.main as m
from app.auth_deps import require_user


def test_trend_without_token_returns_401() -> None:
    client = TestClient(m.app)
    resp = client.post(
        "/trend",
        json={"diagnoses": [{"status": "건강"}, {"status": "병해 의심"}]},
    )
    assert resp.status_code == 401


def test_compare_without_token_returns_401() -> None:
    client = TestClient(m.app)
    resp = client.post(
        "/compare",
        json={"previous": {"status": "건강"}, "current": {"status": "건강"}},
    )
    assert resp.status_code == 401


def test_diagnose_without_token_returns_401() -> None:
    # 과금(Gemini 비전) 엔드포인트 — 토큰 없으면 이미지 처리 전에 401로 끊겨야 한다.
    client = TestClient(m.app)
    resp = client.post(
        "/diagnose",
        files={"file": ("leaf.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert resp.status_code == 401


def test_diagnose_refine_without_token_returns_401() -> None:
    # 과금(gpt-4o-mini) 엔드포인트 — 페이로드 검증(422)보다 인증(401)이 먼저 걸린다.
    client = TestClient(m.app)
    resp = client.post("/diagnose/refine", json={})
    assert resp.status_code == 401


def test_trend_authed_reaches_handler_guard() -> None:
    # 인증을 override로 통과시키면 핸들러의 '2건 미만' 가드(400)에 도달 →
    # 인증 게이트가 정상 통과됨을 LLM 호출 없이 검증.
    m.app.dependency_overrides[require_user] = lambda: "test-uid"
    try:
        client = TestClient(m.app)
        resp = client.post("/trend", json={"diagnoses": [{"status": "건강"}]})
        assert resp.status_code == 400
    finally:
        m.app.dependency_overrides.pop(require_user, None)
