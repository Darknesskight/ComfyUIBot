from comfy_api import queue_prompt, get_history, get_image
from comfy_websocket import add_client, remove_client
from enum import Enum
import json
import threading
import asyncio
import time
import math


class Status(Enum):
    READY = 1
    QUEUED = 2
    RUNNING = 3
    IMAGE_READY = 4
    DONE = 5


class Job(threading.Thread):
    daemon = True

class DrawJob(Job):
    prompt = None
    prompt_id = -1
    state = Status.READY
    followup = None
    msg = None
    last_update = time.time()

    def __init__(self, prompt, followup):
        super().__init__()
        self.prompt = prompt
        self.followup = followup

    async def run(self):
        add_client(self)
        try:
            self.send_prompt()
            await self.wait_for_image()
            return self.get_images(), self.msg
        finally:
            remove_client(self)

    async def wait_for_image(self):
         while(self.state != Status.IMAGE_READY):
                await asyncio.sleep(0.5)

    def send_prompt(self):
        prompt_id = queue_prompt(self.prompt)
        self.prompt_id = prompt_id["prompt_id"]
        self.state = Status.QUEUED

    async def on_message(self, ws_message):
        # Ignore all messages if we are not running.
        if self.state != Status.QUEUED and self.state != Status.RUNNING:
            return
        
        # Ignore preview image message.
        if not isinstance(ws_message, str):
            return
        
        message = json.loads(ws_message)
        data = message['data']

        if message['type'] == 'execution_start':
            await self.on_execution_start(data)

        if message['type'] == 'executing':
            await self.on_executing(data)

        if message['type'] == 'progress':
            await self.on_progress(data)


    async def on_execution_start(self, data):
        if data['prompt_id'] != self.prompt_id:
            return
        self.state = Status.RUNNING

    async def on_progress(self, data):
        if self.state != Status.RUNNING:
            return
        if(time.time() - self.last_update >= 0.5):
            progress = math.floor((data["value"]/data["max"])*10)
            complete = '▓'*progress
            incomplete = '░' * (10-progress)

            if not self.msg:
                self.msg = await self.followup.send(
                    complete + incomplete, wait=True
                )
            else:
                await self.msg.edit(
                    complete + incomplete
                )
            self.last_update = time.time()

    async def on_executing(self, data):
        if data['prompt_id'] != self.prompt_id:
            return
        if data['node'] is None:
            await self.msg.edit(
                "▓▓▓▓▓▓▓▓▓▓"
            )
            self.state = Status.IMAGE_READY

    def get_images(self):
        output_images = {}
        history = get_history(self.prompt_id)[self.prompt_id]
        for o in history['outputs']:
            for node_id in history['outputs']:
                node_output = history['outputs'][node_id]
                if 'images' in node_output:
                    images_output = []
                    for image in node_output['images']:
                        image_data = get_image(image['filename'], image['subfolder'], image['type'])
                        images_output.append(image_data)
                output_images[node_id] = images_output

        return output_images
