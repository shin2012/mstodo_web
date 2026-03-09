#!/Users/yoseop/apps/mstodo/bin/python3
import os
import configparser
import sys
from pymstodo import ToDoConnection

# Variables from existing files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.ini')

def main():
    config = configparser.ConfigParser()
    client_id = None
    client_secret = None
    client_token = None

    # Load existing token from config.ini if it exists
    if os.path.isfile(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if config.has_section('connect'):
            try:
                client_id = config.get('connect', 'client_id')
                client_secret = config.get('connect', 'client_secret')
                # Evaluating the stringified dictionary from config.ini
                client_token = eval(config.get('connect', 'client_token'))
            except:
                client_token = None

    if not client_token or not client_id or not client_secret:
        # If client_id/secret are missing, we can't do much if they're not provided via config
        # For simplicity, we assume they are either in config or it fails.
        # But let's try to get them if they are missing from some sections.
        if not client_id or not client_secret:
            print("Error: client_id and client_secret must be set in config.ini")
            sys.exit(1)

        # Authentication process
        # No need to pass redirect_uri as it's hardcoded in the library
        auth_url = ToDoConnection.get_auth_url(client_id)
        print(f"로그인이 필요합니다. 아래 URL을 브라우저에 붙여넣고 승인해 주세요:\n\n{auth_url}\n")
        print("참고: Azure Portal에 'https://localhost/login/authorized'가 Redirect URI로 등록되어 있어야 합니다.\n")
        redirect_resp = input("승인 후 브라우저 주소창의 최종 URL(https://localhost/login/authorized?code=...)을 여기에 붙여넣어 주세요: ")
        
        try:
            client_token = ToDoConnection.get_token(client_id, client_secret, redirect_resp)
            
            # Save for future use
            if not config.has_section('connect'):
                config.add_section('connect')
            config.set('connect', 'client_id', client_id)
            config.set('connect', 'client_secret', client_secret)
            config.set('connect', 'client_token', str(client_token))
            with open(CONFIG_FILE, 'w') as f:
                config.write(f)
        except Exception as e:
            print(f"인증 오류: {e}")
            sys.exit(1)

    # Connect to To Do
    try:
        todo_client = ToDoConnection(client_id=client_id, client_secret=client_secret, token=client_token)
        lists = todo_client.get_lists()

        print("=== Microsoft To Do 현재 할 일 ===\n")
        has_tasks = False
        target_lists = ["26H1 판매운영부", "Routine tasks"]
        
        for task_list in lists:
            if task_list.displayName not in target_lists:
                continue
                
            tasks = todo_client.get_tasks(task_list.list_id)
            pending_tasks = [t for t in tasks if getattr(t, 'status', '').lower() != 'completed']
            
            if pending_tasks:
                has_tasks = True
                print(f"[{task_list.displayName}]")
                for task in pending_tasks:
                    # Check for due_date (returns datetime object or None)
                    prefix = ""
                    due = task.due_date
                    if due:
                        prefix = f"({due.month}.{due.day}.) "
                    
                    print(f"  - {prefix}{task.title}")
                print()

        if not has_tasks:
            print("완료되지 않은 할 일이 없습니다.")
            
    except Exception as e:
        print(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
