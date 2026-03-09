#!/Users/yoseop/apps/mstodo/bin/python3
import os
import configparser
from pymstodo import ToDoConnection

# Load configuration
config = configparser.ConfigParser()
base_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(base_dir, 'config.ini')

if os.path.isfile(config_file):
    config.read(config_file)
    client_id = config.get('connect', 'client_id')
    client_secret = config.get('connect', 'client_secret')
    client_token = eval(config.get('connect', 'client_token'))
else:
    raise Exception("config.ini not found")

todo_client = ToDoConnection(client_id=client_id, client_secret=client_secret, token=client_token)

lists = todo_client.get_lists()
task_list = lists[0]
tasks = todo_client.get_tasks(task_list.list_id)

print(task_list)
print(*tasks, sep='\n')
