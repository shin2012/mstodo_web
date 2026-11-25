"""mstodo MCP 서버 — Claude(claude.ai / Desktop / Code)에서 할 일을 읽고 쓰는 도구 모음.

mstodo_web의 REST API(/api/*)를 그대로 호출한다. DB에 직접 쓰지 않으므로
Microsoft To Do 동기화 로직은 웹 앱과 동일하게 유지된다.

인증 (oauth_provider.py):
  - claude.ai 커넥터: OAuth 2.1 (동적 등록 + PKCE). 승인 페이지 /consent는 NPM에서 tinyauth 로그인으로 보호.
  - Claude Code 등: Authorization: Bearer <MCP_TOKEN> (정적 토큰)
"""
import os
import re
from datetime import date, datetime, timedelta, timezone

import httpx
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from oauth_provider import TodoOAuthProvider

API_BASE = os.environ.get("TODO_API_BASE", "http://mstodo_web:5001").rstrip("/")
MCP_TOKEN = os.environ.get("MCP_TOKEN", "")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://todo.b-612.kr").rstrip("/")
MCP_BASE = f"{PUBLIC_URL}/mcp"   # MCP 엔드포인트 = OAuth issuer
KST = timezone(timedelta(hours=9))

provider = TodoOAuthProvider(MCP_BASE, static_token=MCP_TOKEN)
_auth = AuthSettings(
    issuer_url=MCP_BASE,
    resource_server_url=MCP_BASE,
    validate_token_resource=False,
    client_registration_options=ClientRegistrationOptions(enabled=True),
    revocation_options=RevocationOptions(enabled=True),
)

try:
    from mcp.server.transport_security import TransportSecuritySettings
    _security = {"transport_security": TransportSecuritySettings(enable_dns_rebinding_protection=False)}
except Exception:  # 구버전 SDK
    _security = {}

mcp = FastMCP(
    "mstodo",
    instructions=(
        "요섭의 Microsoft To Do(할 일) 도구. 날짜는 한국 시간(KST) 기준 YYYY-MM-DD. "
        "목록은 이름 일부만 줘도 찾는다. 작업을 바꾸기 전에 list_tasks/search_tasks로 task_id를 먼저 확인할 것."
    ),
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    auth=_auth,
    auth_server_provider=provider,
    **_security,
)


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request):
    return PlainTextResponse("ok")


@mcp.custom_route("/consent/{rid}", methods=["GET", "POST"])
async def consent(request: Request):
    return await provider.consent(request)

_client = httpx.Client(base_url=API_BASE, timeout=60)


def _api(method: str, path: str, **kw):
    r = _client.request(method, path, **kw)
    try:
        data = r.json()
    except Exception:
        data = {"error": r.text[:500]}
    if r.status_code >= 400:
        msg = data.get("error") if isinstance(data, dict) else data
        raise RuntimeError(f"Todo API {r.status_code}: {msg}")
    return data


def _lists():
    return _api("GET", "/api/lists")


def _resolve_list(name_or_id: str) -> dict:
    lists = _lists()
    for l in lists:
        if l["id"] == name_or_id:
            return l
    key = name_or_id.strip().lower()
    exact = [l for l in lists if l["name"].strip().lower() == key]
    if exact:
        return exact[0]
    part = [l for l in lists if key in l["name"].lower()]
    if len(part) == 1:
        return part[0]
    if not part:
        raise ValueError(f"'{name_or_id}' 목록을 찾지 못함. 사용 가능: " + ", ".join(l["name"] for l in lists))
    raise ValueError(f"'{name_or_id}'에 해당하는 목록이 여러 개: " + ", ".join(l["name"] for l in part))


def _fmt(t: dict) -> dict:
    out = {
        "task_id": t["id"],
        "list_id": t["list_id"],
        "list": t.get("list_name"),
        "title": t["title"],
        "status": t["status"],
        "important": t.get("importance") == "high",
        "due_date": t.get("due_date"),
    }
    subs = t.get("subtasks") or t.get("checklistItems") or []
    if subs:
        out["subtasks"] = [
            {"subtask_id": s.get("id"), "title": s.get("displayName"), "done": bool(s.get("isChecked"))}
            for s in subs
        ]
    if t.get("completed_date_time"):
        out["completed_at"] = t["completed_date_time"]
    return out


def _all_tasks(include_completed: bool = False) -> list[dict]:
    if not include_completed:
        return _api("GET", "/api/tasks")
    tasks = []
    for l in _lists():
        tasks.extend(_api("GET", "/api/tasks", params={"list_id": l["id"]}))
    return tasks


def _find_task(task_id: str) -> dict:
    for t in _api("GET", "/api/tasks"):
        if t["id"] == task_id:
            return t
    for t in _all_tasks(include_completed=True):
        if t["id"] == task_id:
            return t
    raise ValueError(f"task_id '{task_id[:20]}...'를 찾지 못함 (sync_todo 후 다시 시도)")


def _check_date(d: str | None) -> str | None:
    if d in (None, ""):
        return None
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        raise ValueError("due_date는 YYYY-MM-DD 형식")
    datetime.strptime(d, "%Y-%m-%d")
    return d


# ───────────────────────────── 도구 ─────────────────────────────

@mcp.tool()
def list_lists() -> list[dict]:
    """할 일 목록(리스트) 전체를 반환한다. 각 항목: list_id, name."""
    return [{"list_id": l["id"], "name": l["name"]} for l in _lists()]


@mcp.tool()
def list_tasks(
    list_name: str | None = None,
    include_completed: bool = False,
    important_only: bool = False,
    due: str | None = None,
) -> dict:
    """할 일을 조회한다.

    list_name: 목록 이름(일부만 써도 됨) 또는 list_id. 비우면 전체 목록.
    include_completed: 완료된 항목도 포함할지.
    important_only: 중요 표시(별표)만.
    due: 'overdue'(기한 지남) | 'today' | 'week'(오늘~7일 내) | 'none'(기한 없음) | 비우면 전체.
    """
    if list_name:
        l = _resolve_list(list_name)
        tasks = _api("GET", "/api/tasks", params={"list_id": l["id"]})
        if not include_completed:
            tasks = [t for t in tasks if t["status"] != "completed"]
    else:
        tasks = _all_tasks(include_completed)
    if important_only:
        tasks = [t for t in tasks if t.get("importance") == "high"]
    today = datetime.now(KST).date()
    if due:
        def ok(t):
            d = t.get("due_date")
            if due == "none":
                return not d
            if not d:
                return False
            dd = date.fromisoformat(d)
            if due == "overdue":
                return dd < today and t["status"] != "completed"
            if due == "today":
                return dd == today
            if due == "week":
                return today <= dd <= today + timedelta(days=7)
            return True
        tasks = [t for t in tasks if ok(t)]
    return {"today": today.isoformat(), "count": len(tasks), "tasks": [_fmt(t) for t in tasks]}


@mcp.tool()
def search_tasks(query: str, include_completed: bool = False) -> dict:
    """제목이나 하위 작업 이름에 query가 들어간 할 일을 찾는다(대소문자 무시)."""
    q = query.strip().lower()
    hits = []
    for t in _all_tasks(include_completed):
        subs = t.get("subtasks") or t.get("checklistItems") or []
        if q in t["title"].lower() or any(q in (s.get("displayName") or "").lower() for s in subs):
            hits.append(_fmt(t))
    return {"count": len(hits), "tasks": hits}


@mcp.tool()
def add_task(
    title: str,
    list_name: str,
    due_date: str | None = None,
    important: bool = False,
    subtasks: list[str] | None = None,
) -> dict:
    """새 할 일을 추가한다.

    list_name: 넣을 목록 이름(일부 가능) 또는 list_id. 모르면 list_lists로 먼저 확인.
    due_date: YYYY-MM-DD (선택). important: 중요 표시. subtasks: 하위 작업 제목 목록(선택).
    """
    due_date = _check_date(due_date)
    l = _resolve_list(list_name)
    res = _api("POST", "/api/tasks", json={"title": title, "list_id": l["id"]})
    tid = res["task_id"]
    if important:
        _api("PATCH", f"/api/tasks/{l['id']}/{tid}", json={"importance": "high"})
    if due_date:
        _api("PATCH", f"/api/tasks/{l['id']}/{tid}/due", json={"due_date": due_date})
    for s in subtasks or []:
        if s.strip():
            _api("POST", f"/api/subtask/add/{l['id']}/{tid}", json={"title": s})
    return {"ok": True, "task_id": tid, "list": l["name"], "title": title,
            "due_date": due_date, "important": important, "subtasks": subtasks or []}


@mcp.tool()
def complete_task(task_id: str, undo: bool = False) -> dict:
    """할 일을 완료 처리한다. undo=True면 다시 미완료로 되돌린다."""
    t = _find_task(task_id)
    status = "notStarted" if undo else "completed"
    _api("POST", f"/api/complete/{t['list_id']}/{task_id}", json={"status": status})
    return {"ok": True, "title": t["title"], "status": status}


@mcp.tool()
def update_task(
    task_id: str,
    title: str | None = None,
    important: bool | None = None,
    due_date: str | None = None,
    clear_due_date: bool = False,
) -> dict:
    """할 일의 제목/중요 표시/기한을 바꾼다. 바꿀 항목만 넘긴다.
    due_date: YYYY-MM-DD. 기한을 없애려면 clear_due_date=True.
    """
    t = _find_task(task_id)
    lid = t["list_id"]
    payload = {}
    if title is not None:
        payload["title"] = title
    if important is not None:
        payload["importance"] = "high" if important else "normal"
    if payload:
        _api("PATCH", f"/api/tasks/{lid}/{task_id}", json=payload)
    if clear_due_date:
        _api("PATCH", f"/api/tasks/{lid}/{task_id}/due", json={"due_date": None})
    elif due_date:
        _api("PATCH", f"/api/tasks/{lid}/{task_id}/due", json={"due_date": _check_date(due_date)})
    return {"ok": True, "task": _fmt({**_find_task(task_id), "list_name": t.get("list_name")})}


@mcp.tool()
def add_subtask(task_id: str, title: str) -> dict:
    """할 일 아래에 하위 작업(체크리스트 항목)을 추가한다."""
    t = _find_task(task_id)
    res = _api("POST", f"/api/subtask/add/{t['list_id']}/{task_id}", json={"title": title})
    return {"ok": True, "subtask_id": (res.get("item") or {}).get("id"), "title": title}


@mcp.tool()
def set_subtask_done(task_id: str, subtask_id: str, done: bool = True) -> dict:
    """하위 작업을 체크(done=True)하거나 체크 해제한다."""
    t = _find_task(task_id)
    _api("POST", f"/api/subtask/complete/{t['list_id']}/{task_id}/{subtask_id}", json={"checked": done})
    return {"ok": True, "done": done}


@mcp.tool()
def sync_todo() -> dict:
    """Microsoft To Do 서버와 즉시 동기화한다(다른 기기에서 방금 바꾼 내용이 안 보일 때)."""
    return _api("GET", "/api/sync/all")


# ───────────────────────────── ASGI 앱 ─────────────────────────────
# 웹 앱과 같은 도메인(todo.b-612.kr)의 /mcp 아래에서 동작한다. NPM이 /mcp, /.well-known/oauth-* 만 이 컨테이너로 보낸다.
#   /mcp                                         → MCP (Bearer 필수)
#   /mcp/authorize|token|register|revoke|health  → SDK 루트 경로로 변환
#   /mcp/consent/<rid>                           → 승인 페이지 (NPM에서 tinyauth 보호)
#   /.well-known/oauth-authorization-server/mcp  → RFC 8414 경로 삽입 방식
#   /.well-known/oauth-protected-resource/mcp    → SDK가 그대로 제공
_inner = mcp.streamable_http_app()
_AS_META = "/.well-known/oauth-authorization-server"


def _rewrite(path: str) -> str:
    if path.startswith("/mcp/"):
        return path[4:]
    if path == _AS_META + "/mcp":
        return _AS_META
    return path


async def app(scope, receive, send):
    if scope["type"] == "http":
        new = _rewrite(scope["path"])
        if new != scope["path"]:
            scope = dict(scope, path=new, raw_path=new.encode())
    return await _inner(scope, receive, send)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("MCP_PORT", "8095")), proxy_headers=True,
                forwarded_allow_ips="*")
