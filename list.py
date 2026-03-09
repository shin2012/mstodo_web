#!/Users/yoseop/apps/mstodo/bin/python3
import requests
import json
import os
import configparser

def get_access_token() :
	# Set the authentication endpoint URL
	url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

	# Load configuration
	config = configparser.ConfigParser()
	base_dir = os.path.dirname(os.path.abspath(__file__))
	config_file = os.path.join(base_dir, 'config.ini')
	
	if os.path.isfile(config_file):
		config.read(config_file)
		client_id = config.get('connect', 'client_id')
		client_secret = config.get('connect', 'client_secret')
	else:
		raise Exception("config.ini not found")

	# Set the client ID, client secret, and scope
	scope = "https://graph.microsoft.com/.default"

	# Set the grant type to client_credentials
	grant_type = "client_credentials"

	# Set the request body
	data = {
			"client_id": client_id,
			"client_secret": client_secret,
			"scope": scope,
			"grant_type": grant_type
			}

	# Make a POST request to the authentication endpoint URL to get the access token
	response = requests.post(url, data=data)

	# Extract the access token from the response
	access_token = response.json()["access_token"]

	# Print the access token
	#print("Access token:", access_token)
	return access_token

def main() :
	# Set the access token and endpoint URL
	access_token = get_access_token()
	url = "https://graph.microsoft.com/v1.0/ToDo_PythonApp/todo/lists"

	# Set the authorization header using the access token
	headers = {"Authorization": "Bearer " + access_token}

	# Make a GET request to the endpoint URL to get the task list
	response = requests.get(url, headers=headers)
	print(response.json())

	# Convert the response to JSON format
	data = json.loads(response.text)

	# Print the task list
	print("Task list:")
	for task_list in data["value"]:
		print(task_list["displayName"])

if __name__ == '__main__':
	main()
