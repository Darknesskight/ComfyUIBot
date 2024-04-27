from collections.abc import Coroutine
from settings import templateEnv
import discord
import io
import json
from api.comfy_websocket import add_client, remove_client
from enum import Enum
import asyncio
import time
from api.comfy_api import get_history, queue_prompt, get_image
import base64
# from bot.utils import ProgressMessage


class Status(Enum):
    READY = 1
    QUEUED = 2
    RUNNING = 3
    IMAGE_READY = 4
    DONE = 5


async def upscale(
    image: discord.Attachment,
    progress_callback: Coroutine[float, io.BytesIO, None]
):
    imageBytes = await image.read()

    options = {
        "image": base64.b64encode(imageBytes).decode(),
    }

    rendered_template = templateEnv.get_template("upscale.j2").render(**options)

    promptJson = json.loads(rendered_template)
    job = UpscaleJob(promptJson, progress_callback)

    images = await job.run()

    for node_id in images:
        for image_data in images[node_id]:
            return io.BytesIO(image_data)



class UpscaleJob:
    prompt_id = -1
    state = Status.READY
    msg = None
    last_update = time.time()

    def __init__(self, prompt, progress_callback):
        super().__init__()
        self.prompt = prompt
        self.progress_callback = progress_callback

    async def run(self):
        await add_client(self)
        try:
            self.send_prompt()
            await self.wait_for_image()
            return self.get_images()
        finally:
            await remove_client(self)

    async def wait_for_image(self):
        while self.state != Status.IMAGE_READY:
            await asyncio.sleep(0.5)

    def send_prompt(self):
        prompt_id = queue_prompt(self.prompt)
        self.prompt_id = prompt_id["prompt_id"]
        self.state = Status.QUEUED

    async def on_message(self, ws_message):
        # Ignore all messages if we are not running.
        if self.state != Status.QUEUED and self.state != Status.RUNNING:
            return

        # Handle normal messages
        if isinstance(ws_message, str):
            message = json.loads(ws_message)
            data = message["data"]

            if message["type"] == "execution_start":
                await self.on_execution_start(data)

            if message["type"] == "executing":
                await self.on_executing(data)

            if message["type"] == "progress":
                await self.on_progress(data)

    async def on_execution_start(self, data):
        if data["prompt_id"] != self.prompt_id:
            return
        self.state = Status.RUNNING

    async def on_executing(self, data):
        if data["prompt_id"] != self.prompt_id:
            return
        if data["node"] is None:
            self.state = Status.IMAGE_READY

    async def on_progress(self, data):
        if self.state != Status.RUNNING:
            return
        await self.progress_callback(data["value"] / data["max"], None)

    def get_images(self):
        output_images = {}
        history = get_history(self.prompt_id)[self.prompt_id]
        for node_id in history["outputs"]:
            node_output = history["outputs"][node_id]
            if "images" in node_output:
                images_output = []
                for image in node_output["images"]:
                    image_data = get_image(
                        image["filename"], image["subfolder"], image["type"]
                    )
                    images_output.append(image_data)
            output_images[node_id] = images_output
        return output_images
