import websockets
import asyncio
import logging
from settings import server_ip, client_id

logger = logging.getLogger(__name__)

_clients = []
_clients_lock = asyncio.Lock()
_websocket_task = None
_websocket_connected = False


async def add_client(client):
    async with _clients_lock:
        _clients.append(client)


async def remove_client(client):
    async with _clients_lock:
        _clients.remove(client)


async def notify_clients(message):
    async with _clients_lock:
        if not _websocket_connected:
            logger.warning("Websocket not connected, skipping message notification")
            return
        for client in _clients:
            try:
                await client.on_message(message)
            except Exception as e:
                logger.error(f"Error sending message to client: {e}")


async def wsrun():
    """Run websocket connection with proper error handling and startup management"""
    uri = f"ws://{server_ip}/ws?clientId={client_id}"
    retry_delay = 5
    max_retry_delay = 60
    
    while True:
        try:
            logger.info(f"Attempting to connect to websocket at {uri}")
            async with websockets.connect(uri, ping_interval=30, ping_timeout=10) as websocket:
                logger.info("Websocket connection established successfully")
                global _websocket_connected
                _websocket_connected = True
                retry_delay = 5  # Reset retry delay on successful connection
                
                while True:
                    try:
                        message = await websocket.recv()
                        await notify_clients(message)
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("Websocket connection closed by server")
                        break
                    except Exception as e:
                        logger.error(f"Error receiving message: {e}")
                        break
                        
        except asyncio.CancelledError:
            logger.info("Websocket task cancelled")
            _websocket_connected = False
            break
        except Exception as e:
            logger.error(f"Connection to websocket failed: {e}")
            _websocket_connected = False
            logger.info(f"Reconnecting in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            # Exponential backoff up to max_retry_delay
            retry_delay = min(retry_delay * 2, max_retry_delay)


def start_websocket_task(loop):
    """Start the websocket task in the given event loop"""
    global _websocket_task
    logger.info(f"Starting websocket task in loop: {loop}")
    if _websocket_task is None or _websocket_task.done():
        logger.info("Creating new websocket task")
        _websocket_task = loop.create_task(wsrun())
        logger.info(f"Websocket task created: {_websocket_task}")
    else:
        logger.info(f"Websocket task already exists: {_websocket_task}")
    return _websocket_task


def stop_websocket_task():
    """Stop the websocket task gracefully"""
    global _websocket_task, _websocket_connected
    if _websocket_task and not _websocket_task.done():
        _websocket_task.cancel()
        _websocket_connected = False
        logger.info("Websocket task stopped")

def is_websocket_connected():
    """Check if websocket is currently connected"""
    return _websocket_connected
