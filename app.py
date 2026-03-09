import os
import configparser
import json
import secrets
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
    
    # 환경 변수가 있으면 우선적으로 설정 (UI에서 입력하지 않아도 되도록)
    env_id = os.environ.get('MS_CLIENT_ID')
    env_secret = os.environ.get('MS_CLIENT_SECRET')
    if env_id: config.set('connect', 'client_id', env_id)
    if env_secret: config.set('connect', 'client_secret', env_secret)
    
    return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def get_todo_client():
    config = get_config()
    try:
        client_id = config.get('connect', 'client_id', fallback=None)
        client_secret = config.get('connect', 'client_secret', fallback=None)
        token_str = config.get('connect', 'client_token', fallback=None)
        
        if not client_id or not client_secret or not token_str or token_str == 'None':
            return None
            
        client_token = eval(token_str)
        return ToDoConnection(client_id=client_id, client_secret=client_secret, token=client_token)
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
    has_token = config.has_option('connect', 'client_token')
    
    return render_template('settings.html', client_id=client_id, client_secret=client_secret, has_token=has_token)

@app.route('/auth/login')
def auth_login():
    config = get_config()
    try:
        client_id = config.get('connect', 'client_id')
        # 현재 요청의 도메인을 기반으로 redirect_uri 생성
        redirect_uri = url_for('auth_callback', _external=True)
        
        # ToDoConnection._redirect를 명시적으로 설정
        ToDoConnection._redirect = redirect_uri
        
        auth_url = ToDoConnection.get_auth_url(client_id)
        return redirect(auth_url)
    except Exception as e:
        return f"Login Error: {str(e)}", 400

@app.route('/auth/callback')
def auth_callback():
    # Microsoft에서 돌아올 때의 URL 전체를 사용
    callback_url = request.url
    config = get_config()
    try:
        client_id = config.get('connect', 'client_id')
        client_secret = config.get('connect', 'client_secret')
        
        # 토큰 교환 시에도 OAuth2Session 초기화에 사용되는 redirect_uri를 설정해야 함
        ToDoConnection._redirect = url_for('auth_callback', _external=True)
        
        # 토큰 교환 (redirect_resp 인자에 callback_url 전달)
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
        return jsonify([{'id': l.list_id, 'name': l.displayName} for l in lists])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks')
def get_tasks():
    client = get_todo_client()
    if not client: return jsonify({"error": "Not authenticated"}), 401
    
    list_id = request.args.get('list_id')
    try:
        all_tasks = []
        lists = client.get_lists()
        for task_list in lists:
            if list_id and task_list.list_id != list_id:
                continue
                
            tasks = client.get_tasks(task_list.list_id, status='notCompleted')
            for task in tasks:
                all_tasks.append({
                    'id': task.task_id,
                    'list_id': task_list.list_id,
                    'list_name': task_list.displayName,
                    'title': task.title,
                    'due_date': task.dueDateTime['dateTime'] if task.dueDateTime else None,
                    'status': task.status,
                    'importance': task.importance
                })
        
        all_tasks.sort(key=lambda x: (x['due_date'] is None, x['due_date']))
        return jsonify(all_tasks)
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
