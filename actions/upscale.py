from collections.abc import Coroutine
from settings import templateEnv
import discord
import io
import json
import base64
from actions.base_job import ComfyJob

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


class UpscaleJob(ComfyJob):
    """Job class for upscaling operations"""
    
    def __init__(self, prompt, progress_callback):
        super().__init__(prompt, progress_callback)
