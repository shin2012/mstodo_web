#!/Users/yoseop/apps/mstodo/bin/python3
import requests
import json
import os
import configparser

# Set Variables
config_file = 'config.ini'
client_id = ''
client_secret = ''
token_file = 'token.json'

# Create an instance of the ConfigParser class
config_data = configparser.ConfigParser()

if os.path.isfile(config_file):
    config_data.read(config_file)
    client_id = config_data.get('connect', 'client_id')
    client_secret = config_data.get('connect', 'client_secret')
else:
    raise Exception(f"{config_file} not found")

# Function to generate token.json
def generate_token():
    # Perform the client credentials flow
    token_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': 'https://graph.microsoft.com/.default'
    }
    response = requests.post(token_url, data=data)
    token = response.json()

    # Save the token to token.json
    with open(token_file, 'w') as file:
        json.dump(token, file)

# Check if token file exists
if os.path.isfile(token_file):
    # Load the token from file
    with open(token_file, 'r') as file:
        token = json.load(file)
else:
    # Generate the token
    generate_token()

    # Load the generated token from file
    with open(token_file, 'r') as file:
        token = json.load(file)

# Use the token to make API requests
api_url = 'https://graph.microsoft.com/v1.0/me/todo/lists'
headers = {
    'Authorization': f'Bearer {token["access_token"]}',
    'Content-Type': 'application/json'
}
response = requests.get(api_url, headers=headers)
tasks = response.json()

# Process and use the tasks as needed
for task in tasks['value']:
    print("Task:", task['displayName'])

