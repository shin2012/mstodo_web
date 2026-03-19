import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mstodo.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Lists table
    c.execute('''
        CREATE TABLE IF NOT EXISTS lists (
            id TEXT PRIMARY KEY,
            name TEXT,
            wellKnownName TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    ''')
    
    # Tasks table
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            list_id TEXT,
            title TEXT,
            status TEXT,
            importance TEXT,
            due_date TEXT,
            completed_date_time TEXT,
            created_date_time TEXT,
            last_modified_date_time TEXT,
            checklist_items TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    ''')
    
    # Check if completed_date_time column exists, if not add it
    c.execute("PRAGMA table_info(tasks)")
    columns = [column[1] for column in c.fetchall()]
    if 'completed_date_time' not in columns:
        c.execute('ALTER TABLE tasks ADD COLUMN completed_date_time TEXT')

    # Sync tokens table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sync_tokens (
            resource_type TEXT PRIMARY KEY,
            delta_link TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Lists operations
def upsert_lists(lists_data):
    conn = get_db()
    c = conn.cursor()
    for lst in lists_data:
        if lst.get('@removed'):
            c.execute('UPDATE lists SET is_deleted = 1 WHERE id = ?', (lst['id'],))
        else:
            c.execute('''
                INSERT INTO lists (id, name, wellKnownName, is_deleted)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    wellKnownName=excluded.wellKnownName,
                    is_deleted=0
            ''', (lst['id'], lst.get('displayName', ''), lst.get('wellKnownName', 'none')))
    conn.commit()
    conn.close()

def get_active_lists():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, name, wellKnownName FROM lists WHERE is_deleted = 0 ORDER BY name')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Tasks operations
def upsert_tasks(list_id, tasks_data):
    conn = get_db()
    c = conn.cursor()
    for task in tasks_data:
        if task.get('@removed'):
            c.execute('UPDATE tasks SET is_deleted = 1 WHERE id = ?', (task['id'],))
        else:
            due_date_str = None
            if task.get('dueDateTime'):
                dt_str = task['dueDateTime'].get('dateTime', '')
                tz_str = task['dueDateTime'].get('timeZone', '')
                try:
                    # ISO 포맷 파싱 (T00:00:00.0000000 형태 대응)
                    dt_part = dt_str.split('.')[0].replace('Z', '')
                    if 'T' not in dt_part:
                        dt_part += 'T00:00:00'
                    dt = datetime.fromisoformat(dt_part)
                    
                    # MS Graph API는 보통 UTC 00:00으로 기한을 반환함 (KST 기준 전날 15:00일 수 있음)
                    # UTC인 경우 9시간을 더해 한국 시간으로 보정
                    if tz_str == 'UTC':
                        dt += timedelta(hours=9)
                    
                    # 최종 날짜 추출
                    due_date_str = dt.strftime('%Y-%m-%d')
                except Exception as e:
                    due_date_str = dt_str[:10]
            
            completed_dt_str = None
            if task.get('completedDateTime'):
                completed_dt_str = task['completedDateTime'].get('dateTime')
                
            checklist_json = json.dumps(task.get('checklistItems', []))
            
            c.execute('''
                INSERT INTO tasks (id, list_id, title, status, importance, due_date, completed_date_time, created_date_time, last_modified_date_time, checklist_items, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(id) DO UPDATE SET
                    list_id=excluded.list_id,
                    title=excluded.title,
                    status=excluded.status,
                    importance=excluded.importance,
                    due_date=excluded.due_date,
                    completed_date_time=excluded.completed_date_time,
                    created_date_time=excluded.created_date_time,
                    last_modified_date_time=excluded.last_modified_date_time,
                    checklist_items=excluded.checklist_items,
                    is_deleted=0
            ''', (
                task['id'],
                list_id,
                task.get('title', ''),
                task.get('status', 'notStarted'),
                task.get('importance', 'normal'),
                due_date_str,
                completed_dt_str,
                task.get('createdDateTime', ''),
                task.get('lastModifiedDateTime', ''),
                checklist_json
            ))
    conn.commit()
    conn.close()

def get_tasks(list_id=None, list_ids=None, include_completed=False):
    conn = get_db()
    c = conn.cursor()

    status_filter = 'AND status != "completed"' if not include_completed else ''

    if list_ids:
        placeholders = ','.join(['?'] * len(list_ids))
        c.execute(f'SELECT * FROM tasks WHERE list_id IN ({placeholders}) AND is_deleted = 0 {status_filter}', list_ids)
    elif list_id:
        c.execute(f'SELECT * FROM tasks WHERE list_id = ? AND is_deleted = 0 {status_filter}', (list_id,))
    else:
        c.execute(f'SELECT * FROM tasks WHERE is_deleted = 0 {status_filter}')

    rows = c.fetchall()
    conn.close()

    tasks = []
    for row in rows:
        t = dict(row)
        t['checklistItems'] = json.loads(t['checklist_items']) if t['checklist_items'] else []
        tasks.append(t)
    return tasks


def update_task_status_local(task_id, status):
    conn = get_db()
    c = conn.cursor()
    if status == 'completed':
        now_str = datetime.utcnow().isoformat() + 'Z'
        c.execute('UPDATE tasks SET status = ?, completed_date_time = ? WHERE id = ?', (status, now_str, task_id))
    else:
        c.execute('UPDATE tasks SET status = ?, completed_date_time = NULL WHERE id = ?', (status, task_id))
    conn.commit()
    conn.close()


def delete_task_by_id(task_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE tasks SET is_deleted = 1 WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

def update_task_local(task_id, **kwargs):
    conn = get_db()
    c = conn.cursor()
    
    fields = []
    values = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        if k == 'checklist_items':
            values.append(json.dumps(v))
        else:
            values.append(v)
    
    if not fields:
        conn.close()
        return
        
    values.append(task_id)
    query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
    c.execute(query, values)
    conn.commit()
    conn.close()

def get_task_by_id(task_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    row = c.fetchone()
    conn.close()
    if row:
        t = dict(row)
        t['checklistItems'] = json.loads(t['checklist_items']) if t['checklist_items'] else []
        return t
    return None

# Sync tokens operations
def get_sync_token(resource_type):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT delta_link FROM sync_tokens WHERE resource_type = ?', (resource_type,))
    row = c.fetchone()
    conn.close()
    return row['delta_link'] if row else None

def set_sync_token(resource_type, delta_link):
    conn = get_db()
    c = conn.cursor()
    if delta_link:
        c.execute('''
            INSERT INTO sync_tokens (resource_type, delta_link)
            VALUES (?, ?)
            ON CONFLICT(resource_type) DO UPDATE SET delta_link=excluded.delta_link
        ''', (resource_type, delta_link))
    else:
        c.execute('DELETE FROM sync_tokens WHERE resource_type = ?', (resource_type,))
    conn.commit()
    conn.close()
    
def clear_sync_token(resource_type):
    set_sync_token(resource_type, None)

def clear_all_sync_tokens():
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM sync_tokens')
    conn.commit()
    conn.close()

def clear_all_data():
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM lists')
    c.execute('DELETE FROM tasks')
    c.execute('DELETE FROM sync_tokens')
    conn.commit()
    conn.close()
