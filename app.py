import os
import configparser
import json
from flask import Flask, render_template, jsonify, request
from pymstodo import ToDoConnection

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.ini')

# Constants from existing configuration
def get_todo_client():
    config = configparser.ConfigParser()
    if os.path.isfile(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if config.has_section('connect'):
            try:
                client_id = config.get('connect', 'client_id')
                client_secret = config.get('connect', 'client_secret')
                client_token = eval(config.get('connect', 'client_token'))
                return ToDoConnection(client_id=client_id, client_secret=client_secret, token=client_token)
            except Exception as e:
                print(f"Error initializing client: {e}")
    return None

@app.route('/')
def index():
    return render_template('index.html')

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
    app.run(debug=True, port=5001)
