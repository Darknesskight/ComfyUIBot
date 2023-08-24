import json
import urllib.request
import urllib.parse
import threading
import websocket

class ComfyApi:
    def __init__(self, server_ip, client_id):
        self.server_ip = server_ip
        self.client_id = client_id
        self.server_address = "http://{}".format(self.server_ip)

    def queue_prompt(self, prompt):
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req =  urllib.request.Request(f"{self.server_address}/prompt", data=data)
        return json.loads(urllib.request.urlopen(req).read())
    
    def system_info(self):
        req =  urllib.request.Request(f"{self.server_address}/object_info")
        return json.loads(urllib.request.urlopen(req).read())
    
    def get_history(self, prompt_id):
        with urllib.request.urlopen(f"{self.server_address}/history/{prompt_id}") as response:
            return json.loads(response.read())
        
    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"{self.server_address}/view?{url_values}") as response:
            return response.read()


class ComfyWebsocket(threading.Thread, websocket.WebSocketApp):
    daemon = True
    clients = []

    def __init__(self, server_ip, client_id):
        super().__init__()
        self.server_ip = server_ip
        self.client_id = client_id
        self.ws_url = f"ws://{self.server_ip}/ws?clientId={self.client_id}"
    
    def run(self):
        this = self

        def on_open(self):
            print(f"Connected to ComfyUI websocket at {this.ws_url}")

        def on_message(self, message):
            for client in this.clients:
                client.on_message(message)

        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=on_message,
                on_open=on_open
            )
            self.ws.run_forever()
        except Exception as e:
            print(e)
    

    def add_client(self, client):
        self.clients.append(client)

    def remove_client(self, client):
        self.clients.remove(client)