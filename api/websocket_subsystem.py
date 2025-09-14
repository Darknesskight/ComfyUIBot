import websockets
import asyncio
import logging
from settings import server_ip, client_id

logger = logging.getLogger(__name__)


class WebSocketSubsystem:
    """Simple WebSocket subsystem for ComfyUI connections"""
    
    def __init__(self):
        self.task = None
        self.connected = False
        self.running = False
        self.clients = []
        self.clients_lock = asyncio.Lock()
    
    async def start(self, loop):
        """Start the websocket subsystem"""
        if self.running:
            return
        
        self.running = True
        self.task = loop.create_task(self._run())
        logger.info("WebSocket subsystem started")
    
    def stop(self):
        """Stop the websocket subsystem"""
        if not self.running:
            return
        
        self.running = False
        self.connected = False
        
        if self.task:
            self.task.cancel()
            logger.info("WebSocket subsystem stopped")
    
    async def add_client(self, client):
        """Add a client to receive messages"""
        async with self.clients_lock:
            self.clients.append(client)
    
    async def remove_client(self, client):
        """Remove a client"""
        async with self.clients_lock:
            if client in self.clients:
                self.clients.remove(client)
    
    async def _notify_clients(self, message):
        """Send message to all clients"""
        async with self.clients_lock:
            for client in self.clients:
                try:
                    await client.on_message(message)
                except Exception as e:
                    logger.error(f"Client notification error: {e}")
    
    async def _run(self):
        """Main websocket connection loop"""
        uri = f"ws://{server_ip}/ws?clientId={client_id}"
        retry_delay = 5
        
        while self.running:
            try:
                async with websockets.connect(uri, ping_interval=30, ping_timeout=10) as ws:
                    self.connected = True
                    logger.info("WebSocket connected")
                    
                    while self.running and self.connected:
                        try:
                            message = await ws.recv()
                            await self._notify_clients(message)
                        except websockets.exceptions.ConnectionClosed:
                            break
                        except Exception as e:
                            logger.error(f"Receive error: {e}")
                            break
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.connected = False
                if self.running:
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 60)
        
        self.connected = False


# Global instance
_subsystem = WebSocketSubsystem()

# Simple interface
def start_websocket(loop):
    """Start the websocket subsystem"""
    asyncio.create_task(_subsystem.start(loop))

def stop_websocket():
    """Stop the websocket subsystem"""
    _subsystem.stop()

def is_websocket_connected():
    """Check if websocket is connected"""
    return _subsystem.connected


# Client management functions for backward compatibility
async def add_client(client):
    """Add a client to receive websocket messages (backward compatibility)"""
    await _subsystem.add_client(client)

async def remove_client(client):
    """Remove a client from receiving websocket messages (backward compatibility)"""
    await _subsystem.remove_client(client)
