from settings import templateEnv
from api.job_db import add_job
import random
import discord
import textwrap
import io
import json
from api.comfy_websocket import add_client, remove_client
from enum import Enum
import asyncio
import time
from api.comfy_api import get_history, queue_prompt, get_image
import math

class Status(Enum):
    READY = 1
    QUEUED = 2
    RUNNING = 3
    IMAGE_READY = 4
    DONE = 5

async def dream(
    ctx: discord.ApplicationContext | discord.Interaction,
    template,
    view,
    prompt,
    negative_prompt,
    model,
    width,
    height,
    steps,
    seed,
    cfg,
):
    await ctx.response.defer(invisible=False)
    try:
        options = {
            "template": template,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "cfg": cfg,
            "steps": steps,
            "model": model,
            "width": width,
            "height": height,
            "seed": seed or random.randint(1, 4294967294),
        }
        rendered_template = templateEnv.get_template(template).render(**options)

        model_display_name = options["model"].replace(".safetensors", "")
        job_id = add_job(options)
        message = textwrap.dedent(
            f"""\
                {ctx.user.mention} here is your image!
                Prompt: ``{options["prompt"]}``
                Model ``{model_display_name}``
                CFG ``{options["cfg"]}`` - Steps: ``{options["steps"]}`` - Seed ``{options["seed"]}``
                Size ``{options["width"]}``x``{options["height"]}`` Job ID ``{job_id}``
            """
        )

        promptJson = json.loads(rendered_template)
        progress_msg = ProgressMessage(ctx.followup)
        job = DrawJob(promptJson, progress_msg)

        images = await job.run()

        await progress_msg.send_message("Drawing complete. Uploading now.")

        for node_id in images:
            for image_data in images[node_id]:
                file = discord.File(fp=io.BytesIO(image_data), filename="output.png")
                await ctx.channel.send(message, file=file, view=view)
                await progress_msg.delete_message()

    except Exception as e:
        print(e)
        await ctx.followup.send(
            "Unable to create image. Please see log for details"
        )

class DrawJob():
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
        await self.progress_msg.send_progress(data["value"]/data["max"])

    async def on_executing(self, data):
        if data['prompt_id'] != self.prompt_id:
            return
        if data['node'] is None:
            await self.progress_msg.send_progress(1)
            self.state = Status.IMAGE_READY

    def get_images(self):
        output_images = {}
        history = get_history(self.prompt_id)[self.prompt_id]
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
            output_images[node_id] = images_output
        return output_images

class ProgressMessage():
    last_update = time.time()
    msg = None

    def __init__(self, followup):
        super().__init__()
        self.followup = followup

    async def send_progress(self, percentage):
        if(time.time() - self.last_update >= 0.5):
            progress=math.floor(percentage*10)
            complete = '▓'*progress
            incomplete = '░' * (10-progress)
            await self.send_message(complete + incomplete)
            self.last_update = time.time()

    async def send_message(self, message):
        if not self.msg:
            self.msg = await self.followup.send(
                message, wait=True
            )
        else:
            await self.msg.edit(
                message
            )
    
    async def delete_message(self):
        if self.msg:
            await self.msg.delete()