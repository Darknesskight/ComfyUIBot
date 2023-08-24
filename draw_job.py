from comfy_api import ComfyApi, ComfyWebsocket
from enum import Enum
import json
import threading
import asyncio

class Status(Enum):
    READY = 1
    RUNNING = 2
    IMAGE_READY = 3
    DONE = 4


class Job(threading.Thread):
    daemon = True

class DrawJob(Job):
    prompt = None
    prompt_id = -1
    state = Status.READY

    def __init__(self, prompt, conn: ComfyApi, ws: ComfyWebsocket):
        super().__init__()
        self.prompt = prompt
        self.conn = conn
        self.ws = ws

    async def run(self):
        self.state = Status.RUNNING
        self.ws.add_client(self)
        try:
            self.send_prompt()
            await self.wait_for_image()
            return self.get_images()
        finally:
            self.ws.remove_client(self)

    async def wait_for_image(self):
         while(self.state != Status.IMAGE_READY):
                await asyncio.sleep(0.5)

    def send_prompt(self):
        prompt_id = self.conn.queue_prompt(self.prompt)
        self.prompt_id = prompt_id["prompt_id"]

    def on_message(self, ws_message):
        # Ignore all messages if we are not running.
        if self.state != Status.RUNNING:
            return
        
        # Ignore preview image message.
        if not isinstance(ws_message, str):
            return
        
        message = json.loads(ws_message)
        # Ignore messages that don't deal with an executing job.
        if message['type'] != 'executing':
            return
        
        data = message['data']
        # If the job is done.
        if data['node'] is None and data['prompt_id'] == self.prompt_id:
            self.state = Status.IMAGE_READY
            
    def get_images(self):
        output_images = {}
        history = self.conn.get_history(self.prompt_id)[self.prompt_id]
        for o in history['outputs']:
            for node_id in history['outputs']:
                node_output = history['outputs'][node_id]
                if 'images' in node_output:
                    images_output = []
                    for image in node_output['images']:
                        image_data = self.conn.get_image(image['filename'], image['subfolder'], image['type'])
                        images_output.append(image_data)
                output_images[node_id] = images_output

        return output_images
