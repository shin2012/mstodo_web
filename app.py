import os
import configparser
import json
import secrets
import requests
import ast
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from werkzeug.middleware.proxy_fix import ProxyFix
from pymstodo import ToDoConnection
import database

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
# Use a more stable secret key if not provided in env
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_for_persistence_12345')

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

def get_refreshed_token():
    config = get_config()
    token = load_token()
    if not token:
        return None
    
    # Check if expired or about to expire (within 5 minutes)
    expires_at = token.get('expires_at', 0)
    if expires_at < time.time() + 300:
        client_id = config.get('connect', 'client_id')
        client_secret = config.get('connect', 'client_secret')
        refresh_token_val = token.get('refresh_token')
        
        if not refresh_token_val:
            return token # Cannot refresh without refresh_token, try using existing one
            
        print(f"Attempting to refresh token for {client_id}")
        url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token_val,
            'scope': 'openid offline_access Tasks.ReadWrite'
        }
        try:
            resp = requests.post(url, data=data)
            if resp.status_code == 200:
                new_token = resp.json()
                # If refresh_token is missing in response, keep the old one
                if 'refresh_token' not in new_token:
                    new_token['refresh_token'] = refresh_token_val
                
                if 'expires_at' not in new_token:
                    new_token['expires_at'] = int(time.time()) + new_token.get('expires_in', 3600)
                
                config.set('connect', 'client_token', str(new_token))
                save_config(config)
                print("Token refreshed and saved successfully.")
                return new_token
            else:
                print(f"Token refresh failed: {resp.text}")
                # If refresh fails, try using the current token one last time if it's not strictly expired
                if expires_at > time.time():
                    return token
                return None
        except Exception as e:
            print(f"Error during token refresh: {e}")
            return token if expires_at > time.time() else None
            
    return token

def get_todo_client():
    config = get_config()
    try:
        client_id = config.get('connect', 'client_id', fallback=None)
        client_secret = config.get('connect', 'client_secret', fallback=None)
        token = get_refreshed_token()
        
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
        # Ensure offline_access is requested
        ToDoConnection._scope = "openid offline_access Tasks.ReadWrite"
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
        
        # Ensure expires_at is present
        if isinstance(token, dict) and 'expires_at' not in token:
            token['expires_at'] = int(time.time()) + token.get('expires_in', 3600)
            
        config.set('connect', 'client_token', str(token))
        save_config(config)
        return redirect(url_for('index'))
    except Exception as e:
        return f"Authentication Error: {str(e)}", 500

@app.route('/api/lists')
def get_lists():
    token_data = get_refreshed_token()
    if not token_data: return jsonify({"error": "Not authenticated"}), 401
    try:
        lists = database.get_active_lists()
        return jsonify(lists)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks')
def get_tasks():
    token_data = get_refreshed_token()
    if not token_data: return jsonify({"error": "Not authenticated"}), 401
    
    list_id_param = request.args.get('list_id')
    try:
        tasks = database.get_active_tasks(list_id_param)
        
        # Add list_name to tasks for UI
        active_lists = {lst['id']: lst['name'] for lst in database.get_active_lists()}
        
        formatted_tasks = []
        for task in tasks:
            if task['list_id'] not in active_lists:
                continue # Skip tasks whose lists are deleted
            task['list_name'] = active_lists[task['list_id']]
            formatted_tasks.append(task)
            
        if not list_id_param:
            formatted_tasks.sort(key=lambda x: (x['importance'] != 'high', x['list_name'], x['due_date'] is None, x['due_date']))
        else:
            formatted_tasks.sort(key=lambda x: (x['importance'] != 'high', x['due_date'] is None, x['due_date']))
            
        return jsonify(formatted_tasks)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/sync/all')
def sync_all():
    token_data = get_refreshed_token()
    if not token_data: return jsonify({"error": "Not authenticated"}), 401
    
    access_token = token_data.get('access_token')
    headers = {"Authorization": f"Bearer {access_token}"}
    
    list_id_param = request.args.get('list_id')
    has_changes = False
    
    try:
        # 1. Sync lists
        delta_link = database.get_sync_token("lists")
        url = delta_link if delta_link else "https://graph.microsoft.com/v1.0/me/todo/lists/delta"
        
        lists_data = []
        lists_synced = False
        
        while url:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 410:
                database.clear_sync_token("lists")
                url = "https://graph.microsoft.com/v1.0/me/todo/lists/delta"
                continue
            if resp.status_code != 200:
                break
                
            data = resp.json()
            items = data.get('value', [])
            if items:
                has_changes = True
                lists_data.extend(items)
                
            if '@odata.nextLink' in data:
                url = data['@odata.nextLink']
            elif '@odata.deltaLink' in data:
                database.set_sync_token("lists", data['@odata.deltaLink'])
                lists_synced = True
                break
            else:
                break
                
        if lists_data:
            database.upsert_lists(lists_data)
            
        # 2. Sync tasks
        active_lists = database.get_active_lists()
        lists_to_sync = [l for l in active_lists if l['id'] == list_id_param] if list_id_param else active_lists
        
        def sync_list_tasks(task_list):
            nonlocal has_changes
            l_id = task_list['id']
            d_link = database.get_sync_token(f"tasks_{l_id}")
            t_url = d_link if d_link else f"https://graph.microsoft.com/v1.0/me/todo/lists/{l_id}/tasks/delta"
            
            t_data = []
            while t_url:
                t_resp = requests.get(t_url, headers=headers)
                if t_resp.status_code == 410:
                    database.clear_sync_token(f"tasks_{l_id}")
                    t_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{l_id}/tasks/delta"
                    continue
                if t_resp.status_code != 200:
                    break
                    
                t_resp_data = t_resp.json()
                t_items = t_resp_data.get('value', [])
                if t_items:
                    has_changes = True
                    t_data.extend(t_items)
                    
                if '@odata.nextLink' in t_resp_data:
                    t_url = t_resp_data['@odata.nextLink']
                elif '@odata.deltaLink' in t_resp_data:
                    database.set_sync_token(f"tasks_{l_id}", t_resp_data['@odata.deltaLink'])
                    break
                else:
                    break
                    
            if t_data:
                database.upsert_tasks(l_id, t_data)

        # Sync tasks sequentially or with ThreadPool
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(sync_list_tasks, lists_to_sync)
            
        return jsonify({"has_changes": has_changes})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/subtask/complete/<list_id>/<task_id>/<subtask_id>', methods=['POST'])
def complete_subtask(list_id, task_id, subtask_id):
    token_data = get_refreshed_token()
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
            # Update local DB
            task = database.get_task_by_id(task_id)
            if task:
                subtasks = task.get('checklistItems', [])
                for sub in subtasks:
                    if sub['id'] == subtask_id:
                        sub['isChecked'] = is_checked
                        break
                database.update_task_local(task_id, checklist_items=subtasks)
            return jsonify({"success": True})
        else:
            return jsonify({"error": resp.text}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def add_task():
    token_data = get_refreshed_token()
    if not token_data: return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    title = data.get('title')
    list_id = data.get('list_id')
    
    if not title or not list_id:
        return jsonify({"error": "Missing title or list_id"}), 400
        
    try:
        access_token = token_data.get('access_token')
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks"
        resp = requests.post(url, json={"title": title}, headers=headers)
        if resp.status_code == 201:
            task_data = resp.json()
            database.upsert_tasks(list_id, [task_data])
            return jsonify({"success": True, "task_id": task_data['id']})
        else:
            return jsonify({"error": resp.text}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/complete/<list_id>/<task_id>', methods=['POST'])
def complete_task(list_id, task_id):
    token_data = get_refreshed_token()
    if not token_data: return jsonify({"error": "Not authenticated"}), 401
    
    try:
        access_token = token_data.get('access_token')
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks/{task_id}"
        resp = requests.patch(url, json={"status": "completed"}, headers=headers)
        if resp.status_code in [200, 204]:
            database.update_task_status_local(task_id, "completed")
            return jsonify({"success": True})
        else:
            return jsonify({"error": resp.text}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/<list_id>/<task_id>', methods=['PATCH'])
def update_task(list_id, task_id):
    token_data = get_refreshed_token()
    if not token_data: return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    payload = {}
    if 'title' in data: payload['title'] = data['title']
    if 'importance' in data: payload['importance'] = data['importance']
    
    try:
        access_token = token_data.get('access_token')
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks/{task_id}"
        resp = requests.patch(url, json=payload, headers=headers)
        if resp.status_code in [200, 204]:
            database.update_task_local(task_id, **payload)
            return jsonify({"success": True})
        else:
            return jsonify({"error": resp.text}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

GROUPS_FILE = os.path.join(BASE_DIR, 'list_groups.json')

def get_groups():
    default_data = {"groups": [], "ungroupedCollapsed": False}
    if os.path.exists(GROUPS_FILE):
        try:
            with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {"groups": data, "ungroupedCollapsed": False}
                return data
        except:
            return default_data
    return default_data

def save_groups(data):
    with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/api/groups', methods=['GET', 'POST'])
def handle_groups():
    if request.method == 'POST':
        data = request.json
        save_groups(data)
        return jsonify({"success": True})
    return jsonify(get_groups())

@app.route('/api/subtask/update/<list_id>/<task_id>/<subtask_id>', methods=['PATCH'])
def update_subtask(list_id, task_id, subtask_id):
    token_data = get_refreshed_token()
    if not token_data: return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    title = data.get('title')
    
    try:
        access_token = token_data.get('access_token')
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks/{task_id}/checklistItems/{subtask_id}"
        resp = requests.patch(url, json={"displayName": title}, headers=headers)
        if resp.status_code in [200, 204]:
            # Update local DB
            task = database.get_task_by_id(task_id)
            if task:
                subtasks = task.get('checklistItems', [])
                for sub in subtasks:
                    if sub['id'] == subtask_id:
                        sub['displayName'] = title
                        break
                database.update_task_local(task_id, checklist_items=subtasks)
            return jsonify({"success": True})
        else:
            return jsonify({"error": resp.text}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/<list_id>/<task_id>/due', methods=['PATCH'])
def update_task_due(list_id, task_id):
    token_data = get_refreshed_token()
    if not token_data: return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    due_date = data.get('due_date') # Expecting YYYY-MM-DD or None
    
    payload = {"dueDateTime": None}
    if due_date:
        # Microsoft API expects ISO format with timezone. 
        # We'll send it as midnight in the user's apparent timezone (which we've been treating as KST).
        # But Graph API actually prefers UTC. For simplicity, we'll send it as T00:00:00.
        payload["dueDateTime"] = {
            "dateTime": f"{due_date}T00:00:00",
            "timeZone": "UTC"
        }
    
    try:
        access_token = token_data.get('access_token')
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks/{task_id}"
        resp = requests.patch(url, json=payload, headers=headers)
        if resp.status_code in [200, 204]:
            database.update_task_local(task_id, due_date=due_date)
            return jsonify({"success": True})
        else:
            return jsonify({"error": resp.text}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
