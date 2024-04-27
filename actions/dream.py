from collections.abc import Coroutine
from settings import templateEnv, sd_loras, sdxl_loras, sd_template, sdxl_template
import io
import json
from api.comfy_websocket import add_client, remove_client
from models.sd_options import SDOptions, SDType
from enum import Enum
import asyncio
import time
from api.comfy_api import get_history, queue_prompt, get_image
import re


class Status(Enum):
    READY = 1
    QUEUED = 2
    RUNNING = 3
    IMAGE_READY = 4
    DONE = 5


async def dream(
    sd_options: SDOptions,
    progress_callback: Coroutine[float, io.BytesIO, None]
):
    prompt, loras = extract_loras(sd_options.prompt)
    template = sd_template if sd_options.sd_type == SDType.SD else sdxl_template

    options = {
        "prompt": prompt,
        "negative_prompt": sd_options.negative_prompt,
        "cfg": sd_options.cfg,
        "sampler": sd_options.sampler,
        "scheduler": sd_options.scheduler,
        "steps": sd_options.steps,
        "model": sd_options.model,
        "width": sd_options.width,
        "height": sd_options.height,
        "hires": None if sd_options.hires == "None" else sd_options.hires,
        "hires_strength": sd_options.hires_strength,
        "seed": sd_options.seed,
        "loras": loras,
    }

    if options["hires"]:
        options["hires_width"] = options["width"]
        options["hires_height"] = options["height"]
        options["width"] = round_to_multiple(options["width"] / 2, 4)
        options["height"] = round_to_multiple(options["height"] / 2, 4)

    rendered_template = templateEnv.get_template(template).render(**options)
    print(rendered_template)
    promptJson = json.loads(rendered_template)
    job = DrawJob(promptJson, progress_callback)

    images = await job.run()

    for node_id in images:
        for image_data in images[node_id]:
            return io.BytesIO(image_data)


def round_to_multiple(number, multiple):
    return multiple * round(number / multiple)


def extract_loras(prompt):
    clean_prompt = prompt
    lora_regex = "(lora:\S+:\d+\.?\d*)"
    matches = re.findall(lora_regex, prompt)

    prompt_loras = []
    for lora in matches:
        clean_prompt = clean_prompt.replace(lora, "")
        lora_segs = lora.split(":")
        prompt_loras.append({
            "name": lora_segs[1], "strength": lora_segs[2]
        })

    # clean up lora list.
    loras = []
    for lora in prompt_loras:
        for known_lora in [*sd_loras, *sdxl_loras]:
            if lora["name"] == known_lora.name or lora["name"] == known_lora.value:
                loras.append({
                    "name": known_lora.value,
                    "strength": lora.strength
                })
                break

    clean_prompt = clean_prompt.strip()
    return clean_prompt, loras


class DrawJob:
    prompt_id = -1
    state = Status.READY
    msg = None
    last_update = time.time()

    def __init__(self, prompt, progress_callback):
        super().__init__()
        self.prompt = prompt
        self.progress_callback = progress_callback
        self.progress_image = None

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

        # Handle preview image.
        if isinstance(ws_message, bytes) and self.state == Status.RUNNING:
            image_buffer = ws_message[8:]
            self.progress_image = io.BytesIO(image_buffer)

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

    async def on_progress(self, data):
        if self.state != Status.RUNNING:
            return
        await self.progress_callback(data["value"] / data["max"], self.progress_image)

    async def on_executing(self, data):
        if data["prompt_id"] != self.prompt_id:
            return
        if data["node"] is None:
            await self.progress_callback(1, self.progress_image)
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
