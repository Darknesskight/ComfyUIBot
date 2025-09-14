from collections.abc import Coroutine
from settings import templateEnv, sd_loras, sdxl_loras, sd_template, sdxl_template
import io
import json
import logging
from models.sd_options import SDOptions, SDType
import re
from actions.base_job import ComfyJob, Status
from utils.logging_config import get_logger

logger = get_logger(__name__)


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
    logger.debug(f"Rendered template: {rendered_template[:200]}...")  # Log first 200 chars
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
                    "strength": lora["strength"]
                })
                break

    clean_prompt = clean_prompt.strip()
    return clean_prompt, loras


class DrawJob(ComfyJob):
    """Job class for dream/drawing operations"""
    
    def __init__(self, prompt, progress_callback):
        super().__init__(prompt, progress_callback)
