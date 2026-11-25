"""MCP용 OAuth 2.1 인가 서버 (claude.ai 사용자 지정 커넥터용).

흐름: Claude가 /register(동적 클라이언트 등록) → 브라우저로 /authorize →
      /consent 승인 페이지(NPM에서 tinyauth 로그인으로 보호) → 승인 시 인가 코드 발급 →
      Claude가 /token으로 액세스/리프레시 토큰 교환(PKCE는 SDK가 검증).

저장소: /data/oauth_store.json (클라이언트·토큰 유지, 재시작해도 재인증 불필요).
정적 토큰 MCP_TOKEN도 Bearer로 받는다(Claude Code 등 헤더 방식용).
"""
import hmac
import json
import os
import secrets
import threading
import time
from html import escape

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

STORE_PATH = os.environ.get("OAUTH_STORE", "/data/oauth_store.json")
ACCESS_TTL = 60 * 60 * 24          # 1일
REFRESH_TTL = 60 * 60 * 24 * 180   # 180일
CODE_TTL = 300
PENDING_TTL = 600


class TodoOAuthProvider:
    def __init__(self, public_url: str, static_token: str = ""):
        self.public_url = public_url.rstrip("/")
        self.static_token = static_token
        self._lock = threading.Lock()
        self.pending: dict[str, dict] = {}            # rid -> {client_id, params}
        self.codes: dict[str, AuthorizationCode] = {}
        self._load()

    # ── 저장소 ──
    def _load(self):
        self.clients, self.access, self.refresh = {}, {}, {}
        try:
            with open(STORE_PATH) as f:
                d = json.load(f)
            self.clients = {k: OAuthClientInformationFull.model_validate(v) for k, v in d.get("clients", {}).items()}
            self.access = {k: AccessToken.model_validate(v) for k, v in d.get("access", {}).items()}
            self.refresh = {k: RefreshToken.model_validate(v) for k, v in d.get("refresh", {}).items()}
        except FileNotFoundError:
            pass

    def _save(self):
        now = time.time()
        self.access = {k: v for k, v in self.access.items() if not v.expires_at or v.expires_at > now}
        self.refresh = {k: v for k, v in self.refresh.items() if not v.expires_at or v.expires_at > now}
        d = {
            "clients": {k: v.model_dump(mode="json") for k, v in self.clients.items()},
            "access": {k: v.model_dump(mode="json") for k, v in self.access.items()},
            "refresh": {k: v.model_dump(mode="json") for k, v in self.refresh.items()},
        }
        os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
        tmp = STORE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(d, f)
        os.chmod(tmp, 0o600)
        os.replace(tmp, STORE_PATH)

    # ── 클라이언트 ──
    async def get_client(self, client_id: str):
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull):
        with self._lock:
            self.clients[client_info.client_id] = client_info
            self._save()

    # ── 인가 ──
    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        now = time.time()
        self.pending = {k: v for k, v in self.pending.items() if v["at"] > now - PENDING_TTL}
        rid = secrets.token_urlsafe(24)
        self.pending[rid] = {"client_id": client.client_id, "params": params, "at": now}
        return f"{self.public_url}/consent/{rid}"

    async def consent(self, request: Request) -> Response:
        """승인 페이지. NPM에서 tinyauth 로그인 뒤에만 도달한다."""
        # rid는 경로에 둔다(로그인 리다이렉트에서 쿼리스트링이 빠지기 때문)
        rid = request.path_params.get("rid", "")
        form = await request.form() if request.method == "POST" else {}
        p = self.pending.get(rid)
        if not p or p["at"] < time.time() - PENDING_TTL:
            return HTMLResponse(_page("요청이 만료되었습니다", "Claude에서 연결을 다시 시도해 주세요."), status_code=400)
        client = self.clients.get(p["client_id"])
        params: AuthorizationParams = p["params"]
        name = escape(client.client_name or "알 수 없는 앱") if client else "알 수 없는 앱"
        redirect_host = escape(params.redirect_uri.host or "")

        if request.method == "GET":
            body = f"""
              <p><b>{name}</b>이(가) 할 일 목록을 읽고 추가·수정·완료하려고 합니다.</p>
              <p class=sub>돌아갈 주소: {redirect_host}</p>
              <form method=post>
                <button name=action value=allow class=ok>허용</button>
                <button name=action value=deny class=no>거부</button>
              </form>"""
            return HTMLResponse(_page("Todo 연결 요청", body))

        self.pending.pop(rid, None)
        if form.get("action") != "allow":
            return RedirectResponse(construct_redirect_uri(str(params.redirect_uri), error="access_denied",
                                                           state=params.state), status_code=302)
        code = secrets.token_urlsafe(32)
        self.codes[code] = AuthorizationCode(
            code=code, scopes=params.scopes or [], expires_at=time.time() + CODE_TTL,
            client_id=p["client_id"], code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource, subject="yoseop",
        )
        return RedirectResponse(construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state),
                                status_code=302)

    async def load_authorization_code(self, client, authorization_code: str):
        c = self.codes.get(authorization_code)
        if c and c.client_id == client.client_id and c.expires_at > time.time():
            return c
        return None

    def _issue(self, client_id, scopes, resource, subject) -> OAuthToken:
        now = int(time.time())
        at, rt = secrets.token_urlsafe(32), secrets.token_urlsafe(40)
        self.access[at] = AccessToken(token=at, client_id=client_id, scopes=scopes, expires_at=now + ACCESS_TTL,
                                      resource=resource, subject=subject)
        self.refresh[rt] = RefreshToken(token=rt, client_id=client_id, scopes=scopes, expires_at=now + REFRESH_TTL,
                                        resource=resource, subject=subject)
        self._save()
        return OAuthToken(access_token=at, token_type="Bearer", expires_in=ACCESS_TTL, refresh_token=rt,
                          scope=" ".join(scopes) if scopes else None)

    async def exchange_authorization_code(self, client, authorization_code: AuthorizationCode):
        with self._lock:
            if self.codes.pop(authorization_code.code, None) is None:
                raise TokenError("invalid_grant", "authorization code already used")
            return self._issue(client.client_id, authorization_code.scopes, authorization_code.resource,
                               authorization_code.subject)

    async def load_refresh_token(self, client, refresh_token: str):
        t = self.refresh.get(refresh_token)
        if t and t.client_id == client.client_id and (not t.expires_at or t.expires_at > time.time()):
            return t
        return None

    async def exchange_refresh_token(self, client, refresh_token: RefreshToken, scopes: list[str]):
        with self._lock:
            self.refresh.pop(refresh_token.token, None)   # 회전
            return self._issue(client.client_id, scopes or refresh_token.scopes, refresh_token.resource,
                               refresh_token.subject)

    async def load_access_token(self, token: str):
        if self.static_token and hmac.compare_digest(token, self.static_token):
            return AccessToken(token=token, client_id="static", scopes=[], expires_at=None, subject="yoseop")
        t = self.access.get(token)
        if t and (not t.expires_at or t.expires_at > time.time()):
            return t
        return None

    async def revoke_token(self, token):
        with self._lock:
            self.access.pop(token.token, None)
            self.refresh.pop(token.token, None)
            self._save()


def _page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang=ko><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>{title}</title>
<style>
body{{font-family:-apple-system,'Pretendard',sans-serif;background:#f5f4f1;margin:0;display:flex;min-height:100vh;align-items:center;justify-content:center}}
.card{{background:#fff;border-radius:16px;padding:28px 24px;max-width:360px;width:88%;box-shadow:0 4px 20px rgba(0,0,0,.08)}}
h1{{font-size:20px;margin:0 0 14px}} p{{line-height:1.5;margin:8px 0}} .sub{{color:#888;font-size:13px}}
form{{display:flex;gap:10px;margin-top:20px}} button{{flex:1;padding:14px;font-size:16px;border:0;border-radius:10px;-webkit-appearance:none}}
.ok{{background:#2b6cdf;color:#fff}} .no{{background:#e9e7e3;color:#333}}
</style></head><body><div class=card><h1>{title}</h1>{body}</div></body></html>"""
