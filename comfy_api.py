import json
import urllib.request
import urllib.parse
from settings import server_ip, client_id

def get_address():
    return "http://{}".format(server_ip)

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request(f"{get_address()}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_system_info():
    req =  urllib.request.Request(f"{get_address()}/object_info")
    return json.loads(urllib.request.urlopen(req).read())

def get_history(prompt_id):
    with urllib.request.urlopen(f"{get_address()}/history/{prompt_id}") as response:
        return json.loads(response.read())
    
def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"{get_address()}/view?{url_values}") as response:
        return response.read()
