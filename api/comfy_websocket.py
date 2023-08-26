import websockets
from settings import server_ip, client_id

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
