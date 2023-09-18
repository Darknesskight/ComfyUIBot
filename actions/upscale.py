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
from bot.utils import ProgressMessage


class Status(Enum):
    READY = 1
    QUEUED = 2
    RUNNING = 3
    IMAGE_READY = 4
    DONE = 5

async def upscale(
    ctx: discord.ApplicationContext | discord.Interaction,
    image: discord.Attachment,
    view
):
    await ctx.response.defer(invisible=False)
    try:
        imageBytes = await image.read()

        options = {
            "image": base64.b64encode(imageBytes).decode(),
        }
        
        rendered_template = templateEnv.get_template("upscale.j2").render(**options)
        
        message = f"{ctx.user.mention} here is your upsclaed image!"

        promptJson = json.loads(rendered_template)
        progress_msg = ProgressMessage(ctx.followup)
        job = UpscaleJob(promptJson, progress_msg)

        images = await job.run()

        await progress_msg.send_message("Upscale complete. Uploading now.")

        for node_id in images:
            for image_data in images[node_id]:
                file = discord.File(fp=io.BytesIO(image_data), filename="output.png")
                await ctx.channel.send(message, file=file, view=view)
                await progress_msg.delete_message()

    except Exception as e:
        print(e)
        await ctx.followup.send("Unable to upscale image. Please see log for details")


class UpscaleJob:
    prompt_id = -1
    state = Status.READY
    msg = None
    last_update = time.time()

    def __init__(self, prompt, progress_msg):
        super().__init__()
        self.prompt = prompt
        self.progress_msg = progress_msg

    async def run(self):
        add_client(self)
        try:
            self.send_prompt()
            await self.wait_for_image()
            return self.get_images()
        finally:
            remove_client(self)

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


    async def on_execution_start(self, data):
        if data["prompt_id"] != self.prompt_id:
            return
        self.state = Status.RUNNING

    async def on_executing(self, data):
        if data["prompt_id"] != self.prompt_id:
            return
        if data["node"] is None:
            self.state = Status.IMAGE_READY

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
