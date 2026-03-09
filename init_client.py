#!/Users/yoseop/apps/mstodo/bin/python3
import os, configparser, pickle, base64
from pymstodo import ToDoConnection

# Set Variables
config_file   = 'config.ini'
client_id     = ''
client_secret = ''
client_token  = ''

# Create an instance of the ConfigParser class
config_data = configparser.ConfigParser()

if os.path.isfile(config_file):
    config_data.read(config_file)
    client_id     = config_data.get('connect', 'client_id')
    client_secret = config_data.get('connect', 'client_secret')
    try:
        client_token  = config_data.get('connect', 'client_token')
    except configparser.NoOptionError:
        client_token = ''
else:
    raise Exception(f"{config_file} not found. Please provide one with [connect] section containing client_id and client_secret.")

if not client_token:
    auth_url = ToDoConnection.get_auth_url(config_data['connect']['client_id'])
    redirect_resp = input(f'Go here and authorize:\n{auth_url}\n\nPaste the full redirect URL below:\n')
    client_token = ToDoConnection.get_token(config_data['connect']['client_id'], 
                                            config_data['connect']['client_secret'], 
                                            redirect_resp)

    client_id     = config_data['connect']['client_id']
    client_secret = config_data['connect']['client_secret']
    config_data['connect']['client_token'] = str(client_token)
    
    # Save the preferences to an INI file
    with open('config.ini', 'w') as configfile:
        config_data.write(configfile)

token = client_token

todo_client = ToDoConnection(client_id=client_id, client_secret=client_secret, token=client_token)

lists = todo_client.get_lists()
task_list = lists[0]
tasks = todo_client.get_tasks(task_list.list_id)

print(task_list)
print(*tasks, sep='\n')
