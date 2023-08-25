import websockets
from settings import server_ip, client_id
import threading

_clients = []

def add_client(client):
    _clients.append(client)

def remove_client(client):
    _clients.remove(client)



async def wsrun():
    async with websockets.connect(f"ws://{server_ip}/ws?clientId={client_id}") as websocket:
        while True:
            mesage = await websocket.recv()
            for client in _clients:
                await client.on_message(mesage)


# def open_connection():
#     def on_open(ws):
#         print(f"Connected to ComfyUI websocket at ws://{server_ip}/ws?clientId={client_id}")

#     def on_message(ws, message):
#         for client in _clients:
#             client.on_message(message)

#     try:
#         ws = websocket.WebSocketApp(
#             f"ws://{server_ip}/ws?clientId={client_id}",
#             on_message=on_message,
#             on_open=on_open
#         )
#         wst = threading.Thread(target=ws.run_forever, daemon=True)
#         wst.start()
#     except Exception as e:
#         print(e)