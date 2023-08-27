from typing import List
from discord import OptionChoice, SelectOption
from dotenv import load_dotenv
import jinja2
import os
import uuid

load_dotenv()

server_ip = os.getenv("COMFY_IP")
client_id = str(uuid.uuid4())
bot_token = os.getenv("BOT_TOKEN")

sd_models: List[OptionChoice] = []
sdxl_models: List[OptionChoice] = []

sd_select_models: List[SelectOption] = []
sdxl_select_models: List[SelectOption] = []

sd_loras: List[OptionChoice] = []
sdxl_loras: List[OptionChoice] = []

sd_select_loras: List[SelectOption] = []
sdxl_select_loras: List[SelectOption] = []

size_range = range(192, 1088, 64)

default_sd_negs = "nsfw, embedding:bad-artist-anime, embedding:bad-artist, watermark, text, error, blurry, jpeg artifacts, cropped, worst quality, low quality, normal quality, jpeg artifacts, (signature), watermark, username, artist name, (worst quality, low quality:1.4), bad anatomy"
default_sdxl_negs = "(worst quality,low quality:1.2),(bad anatomy),(3d:1.2),blurry, watermark, signature, ugly, poorly drawn, embedding:unaestheticXLv13"
default_sd_model = "sd-1.5\\meinapastel_v6Pastel.safetensors"
default_sdxl_model = "sdxl-1.0\\sdxlUnstableDiffusers_v5UnchainedSlayer.safetensors"

default_steps = 20
default_cfg = 8

templateLoader = jinja2.FileSystemLoader(searchpath="./templates")
templateEnv = jinja2.Environment(loader=templateLoader)

sd_template = "sd-1.5.j2"
sdxl_template = "sdxl-1.0.j2"

def set_comfy_settings(system_info):
    models: List[str] = system_info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    for model in models:
        if model.startswith('sd-1.5\\'):
            sd_models.append(
                OptionChoice(
                    model.replace('sd-1.5\\', '').replace('.safetensors', ''),
                    model
                )
            )
            sd_select_models.append(
                SelectOption(
                    label=model.replace('sd-1.5\\', '').replace('.safetensors', ''),
                    value=model
                )
            )
        elif model.startswith('sdxl-1.0\\'):
            sdxl_models.append(
                OptionChoice(model.replace('sdxl-1.0\\', '').replace('.safetensors', ''), model)
            )
            sdxl_select_models.append(
                SelectOption(
                    label=model.replace('sdxl-1.0\\', '').replace('.safetensors', ''),
                    value=model
                )
            )
        else:
            print(f"Unknown model type for {model}")

    loras: List[str] = system_info["LoraLoader"]["input"]["required"]["lora_name"][0]
    for lora in loras:
        if lora.startswith('sd-1.5\\'):
            sd_loras.append(
                OptionChoice(
                    lora.replace('sd-1.5\\', '').replace('.safetensors', ''),
                    lora
                )
            )
            sd_select_loras.append(
                SelectOption(
                    label=lora.replace('sd-1.5\\', '').replace('.safetensors', ''),
                    value=lora
                )
            )
        elif lora.startswith('sdxl-1.0\\'):
            sdxl_loras.append(
                OptionChoice(lora.replace('sdxl-1.0\\', '').replace('.safetensors', ''), lora)
            )
            sdxl_select_loras.append(
                SelectOption(
                    label=lora.replace('sdxl-1.0\\', '').replace('.safetensors', ''),
                    value=lora
                )
            )
        else:
            print(f"Unknown lora type for {lora}")
