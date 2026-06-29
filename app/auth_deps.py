"""[인증 통합] Firebase ID 토큰 검증 — 보호 엔드포인트(/compare·/trend)용 FastAPI 의존성.

프론트가 `Authorization: Bearer <Firebase ID 토큰>`으로 보내면 firebase-admin이 검증하고
uid를 반환한다. 토큰 부재/위조/만료 시 401, firebase-admin 구성 실패 시 503.

- 초기화는 기존 Vertex와 동일한 Application Default Credentials를 재사용하고, 검증 대상
  Firebase 프로젝트는 `FIREBASE_PROJECT_ID` env로 지정한다(= 프론트 NEXT_PUBLIC_FIREBASE_PROJECT_ID).
- firebase_admin import는 함수 내부에서만(지연) — 미설치 환경에서 app.main collect가 깨지지 않게.
"""

from __future__ import annotations

import logging
import os
import threading

from fastapi import Header, HTTPException

logger = logging.getLogger("plant_api")

_init_lock = threading.Lock()
_initialized = False


def _ensure_firebase_app() -> None:
    """firebase-admin 앱을 1회 초기화(지연·스레드 안전). 실패 시 예외를 올림."""
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:  # 이미 초기화된 앱이 있으면 재사용
            project_id = (os.getenv("FIREBASE_PROJECT_ID") or "").strip()
            options = {"projectId": project_id} if project_id else None
            firebase_admin.initialize_app(credentials.ApplicationDefault(), options)
        _initialized = True


async def require_user(authorization: str | None = Header(default=None)) -> str:
    """`Authorization: Bearer <Firebase ID 토큰>` 검증 → uid 반환.

    헤더 부재/형식 오류/토큰 위조 → 401. firebase-admin 구성 실패 → 503(서버 측 문제).
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    try:
        _ensure_firebase_app()
    except Exception as e:
        logger.exception("firebase-admin 초기화 실패")
        raise HTTPException(status_code=503, detail="인증 서버 구성 오류입니다.") from e

    from firebase_admin import auth as fb_auth

    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception as e:
        logger.warning("Firebase 토큰 검증 실패: %s", e)
        raise HTTPException(status_code=401, detail="유효하지 않은 인증 토큰입니다.") from e

    uid = decoded.get("uid") or decoded.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="유효하지 않은 인증 토큰입니다.")
    return str(uid)
