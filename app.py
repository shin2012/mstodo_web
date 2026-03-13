import os
import configparser
import json
import secrets
import requests
import ast
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from werkzeug.middleware.proxy_fix import ProxyFix
from pymstodo import ToDoConnection

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(24))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.ini')

def get_config():
    config = configparser.ConfigParser()
    if os.path.isfile(CONFIG_FILE):
        config.read(CONFIG_FILE)
    if not config.has_section('connect'):
        config.add_section('connect')
    
    env_id = os.environ.get('MS_CLIENT_ID')
    env_secret = os.environ.get('MS_CLIENT_SECRET')
    if env_id: config.set('connect', 'client_id', env_id)
    if env_secret: config.set('connect', 'client_secret', env_secret)
    
    return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def load_token():
    config = get_config()
    token_str = config.get('connect', 'client_token', fallback=None)
    if token_str and token_str != 'None':
        try:
            return ast.literal_eval(token_str)
        except:
            return None
    return None

def get_todo_client():
    config = get_config()
    try:
        client_id = config.get('connect', 'client_id', fallback=None)
        client_secret = config.get('connect', 'client_secret', fallback=None)
        token = load_token()
        
        if not client_id or not client_secret or not token:
            return None
            
        return ToDoConnection(client_id=client_id, client_secret=client_secret, token=token)
    except Exception as e:
        print(f"Error initializing client: {e}")
        return None

@app.route('/')
def index():
    if not get_todo_client():
        return redirect(url_for('settings'))
    return render_template('index.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    config = get_config()
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        client_secret = request.form.get('client_secret')
        if client_id and client_secret:
            config.set('connect', 'client_id', client_id)
            config.set('connect', 'client_secret', client_secret)
            save_config(config)
            return redirect(url_for('settings'))

    client_id = config.get('connect', 'client_id', fallback='')
    client_secret = config.get('connect', 'client_secret', fallback='')
    has_token = load_token() is not None
    
    return render_template('settings.html', client_id=client_id, client_secret=client_secret, has_token=has_token)

@app.route('/auth/login')
def auth_login():
    config = get_config()
    try:
        client_id = config.get('connect', 'client_id')
        ToDoConnection._redirect = url_for('auth_callback', _external=True)
        return redirect(ToDoConnection.get_auth_url(client_id))
    except Exception as e:
        return f"Login Error: {str(e)}", 400

@app.route('/auth/callback')
def auth_callback():
    callback_url = request.url
    config = get_config()
    try:
        client_id = config.get('connect', 'client_id')
        client_secret = config.get('connect', 'client_secret')
        ToDoConnection._redirect = url_for('auth_callback', _external=True)
        token = ToDoConnection.get_token(client_id, client_secret, callback_url)
        config.set('connect', 'client_token', str(token))
        save_config(config)
        return redirect(url_for('index'))
    except Exception as e:
        return f"Authentication Error: {str(e)}", 500

@app.route('/api/lists')
def get_lists():
    client = get_todo_client()
    if not client: return jsonify({"error": "Not authenticated"}), 401
    try:
        lists = client.get_lists()
        return jsonify([{'id': l.list_id, 'name': l.displayName, 'wellKnownName': getattr(l, 'wellKnownName', 'none')} for l in lists])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks')
def get_tasks():
    token_data = load_token()
    if not token_data: return jsonify({"error": "Not authenticated"}), 401
    
    client = get_todo_client()
    if not client: return jsonify({"error": "Client init failed"}), 500

    list_id = request.args.get('list_id')
    try:
        lists = client.get_lists()
        if list_id:
            lists = [l for l in lists if l.list_id == list_id]

        all_tasks = []
        access_token = token_data.get('access_token')
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # 리스트를 20개씩 끊어서 Batch 처리
        for i in range(0, len(lists), 20):
            chunk = lists[i:i+20]
            requests_payload = []
            for idx, task_list in enumerate(chunk):
                requests_payload.append({
                    "id": str(idx),
                    "method": "GET",
                    "url": f"/me/todo/lists/{task_list.list_id}/tasks?$filter=status ne 'completed'&$expand=checklistItems"
                })
            
            batch_resp = requests.post("https://graph.microsoft.com/v1.0/$batch", 
                                     json={"requests": requests_payload}, 
                                     headers=headers)
            
            if batch_resp.status_code == 200:
                responses = batch_resp.json().get('responses', [])
                for resp in responses:
                    original_idx = int(resp.get('id'))
                    task_list = chunk[original_idx]
                    if resp.get('status') == 200:
                        tasks_data = resp.get('body', {}).get('value', [])
                        for task in tasks_data:
                            due_date = None
                            if task.get('dueDateTime'):
                                try:
                                    dt_str = task['dueDateTime']['dateTime'].split('.')[0]
                                    dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
                                    kst_dt = dt + timedelta(hours=9)
                                    due_date = kst_dt.strftime('%Y-%m-%d')
                                except:
                                    due_date = task['dueDateTime']['dateTime'].split('T')[0]
                            
                            all_tasks.append({
                                'id': task['id'],
                                'list_id': task_list.list_id,
                                'list_name': task_list.displayName,
                                'title': task['title'],
                                'due_date': due_date,
                                'status': task['status'],
                                'importance': task['importance'],
                                'subtasks': task.get('checklistItems', [])
                            })
        
        if not list_id:
            all_tasks.sort(key=lambda x: (x['list_name'], x['due_date'] is None, x['due_date']))
        else:
            all_tasks.sort(key=lambda x: (x['due_date'] is None, x['due_date']))
            
        return jsonify(all_tasks)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/subtask/complete/<list_id>/<task_id>/<subtask_id>', methods=['POST'])
def complete_subtask(list_id, task_id, subtask_id):
    token_data = load_token()
    if not token_data: return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    is_checked = data.get('checked', False)
    
    try:
        access_token = token_data.get('access_token')
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks/{task_id}/checklistItems/{subtask_id}"
        resp = requests.patch(url, json={"isChecked": is_checked}, headers=headers)
        if resp.status_code in [200, 204]:
            return jsonify({"success": True})
        else:
            return jsonify({"error": resp.text}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def add_task():
    client = get_todo_client()
    if not client: return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    title = data.get('title')
    list_id = data.get('list_id')
    
    if not title or not list_id:
        return jsonify({"error": "Missing title or list_id"}), 400
        
    try:
        task = client.create_task(title, list_id)
        return jsonify({"success": True, "task_id": task.task_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/complete/<list_id>/<task_id>', methods=['POST'])
def complete_task(list_id, task_id):
    client = get_todo_client()
    if not client: return jsonify({"error": "Not authenticated"}), 401
    try:
        client.complete_task(task_id, list_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
