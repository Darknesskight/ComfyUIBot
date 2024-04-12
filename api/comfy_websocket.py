import websockets
import asyncio
from settings import server_ip, client_id

_clients = []
_clients_lock = asyncio.Lock()


async def add_client(client):
    async with _clients_lock:
        _clients.append(client)


async def remove_client(client):
    async with _clients_lock:
        _clients.remove(client)


async def notify_clients(message):
    async with _clients_lock:
        for client in _clients:
            try:
                await client.on_message(message)
            except Exception as e:
                print(f"Error sending message to client: {e}")


async def wsrun():
    uri = f"ws://{server_ip}/ws?clientId={client_id}"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                while True:
                    message = await websocket.recv()
                    await notify_clients(message)
        except Exception as e:
            print(f"Connection to websocket lost. Reconnecting in 5 seconds... {e}")
            await asyncio.sleep(5)  # Wait before reconnecting
