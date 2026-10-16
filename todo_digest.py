#!/usr/bin/env python3
"""매일 아침 '오늘 마감 + 기한 지난 할 일'을 푸시로 보냄 (crontab 08:00)

1. 앱의 동기화를 한 번 돌려 Microsoft To Do 최신 상태 반영
2. mstodo.db 에서 미완료 + 마감일 <= 오늘 인 항목 조회
3. 하나라도 있으면 push-service 로 발송 (app=todo), 없으면 보내지 않음
"""
import datetime
import json
import os
import sqlite3
import subprocess
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "mstodo.db")
PUSH_SH = "/home/yoseop/apps/push-service/push.sh"
MAX_LINES = 6


def sync():
    try:
        urllib.request.urlopen("http://127.0.0.1:5001/api/sync/all?force=1", timeout=300).read()
    except Exception as e:  # 동기화 실패해도 기존 데이터로 계속 진행
        print("동기화 실패:", e)


def due_tasks(today: str):
    c = sqlite3.connect(DB)
    try:
        return c.execute(
            """SELECT t.due_date, t.title, t.importance, l.name
               FROM tasks t LEFT JOIN lists l ON l.id = t.list_id
               WHERE t.is_deleted = 0 AND t.status != 'completed'
                 AND t.due_date IS NOT NULL AND t.due_date <= ?
               ORDER BY t.due_date, t.importance = 'high' DESC, t.title""",
            (today,)).fetchall()
    finally:
        c.close()


def main():
    today = os.getenv("TODO_DIGEST_DATE") or datetime.date.today().isoformat()  # 테스트용 날짜 지정 가능
    sync()
    rows = due_tasks(today)
    if not rows:
        print(today, "오늘 마감/지난 할 일 없음 — 발송 안 함")
        return
    todays = [r for r in rows if r[0] == today]
    overdue = [r for r in rows if r[0] < today]

    parts = []
    if todays:
        parts.append(f"오늘 {len(todays)}개")
    if overdue:
        parts.append(f"기한 지남 {len(overdue)}개")
    title = "📋 할 일 · " + ", ".join(parts)

    lines = []
    for due, name, imp, _lst in todays + overdue:
        mark = "⭐ " if imp == "high" else ""
        late = "" if due == today else f" ({due[5:].replace('-', '/')})"
        lines.append(f"• {mark}{name}{late}")
    if len(lines) > MAX_LINES:
        lines = lines[:MAX_LINES] + [f"외 {len(rows) - MAX_LINES}개"]
    body = "\n".join(lines)

    out = subprocess.run([PUSH_SH, title, body, "todo", "https://todo.b-612.kr/", "todo-digest"],
                         capture_output=True, text=True, timeout=120)
    print(today, title, out.stdout.strip() or out.stderr.strip())


if __name__ == "__main__":
    main()
