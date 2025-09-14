from typing import List
from discord import OptionChoice, SelectOption
from dotenv import load_dotenv
import jinja2
import os
import uuid
import logging

logger = logging.getLogger(__name__)

load_dotenv()

server_ip = os.getenv("COMFY_IP")
client_id = str(uuid.uuid4())
bot_token = os.getenv("BOT_TOKEN")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_model = "gpt-4o-mini"
openai_truncate_limit = 10500


sd_models: List[OptionChoice] = []
sdxl_models: List[OptionChoice] = []

samplers: List[OptionChoice] = []
schedulers: List[OptionChoice] = []

sd_select_models: List[SelectOption] = []
sdxl_select_models: List[SelectOption] = []

sd_loras: List[OptionChoice] = []
sdxl_loras: List[OptionChoice] = []

upscale_latent: List[str] = ["None"]

size_range = range(192, 1218, 64)

templateLoader = jinja2.FileSystemLoader(searchpath="./templates")
templateEnv = jinja2.Environment(loader=templateLoader)

sd_template = "sd-1.5.j2"
sdxl_template = "sdxl-1.0.j2"


async def set_comfy_settings(system_info):
    """Set ComfyUI settings from system info data"""
    logger.info(f"Setting comfy settings with system info keys: {list(system_info.keys())}")
    
    try:
        # Clear existing lists to avoid duplicates
        sd_models.clear()
        sdxl_models.clear()
        sd_select_models.clear()
        sdxl_select_models.clear()
        sd_loras.clear()
        sdxl_loras.clear()
        samplers.clear()
        schedulers.clear()
        upscale_latent.clear()
        upscale_latent.append("None")  # Reset to default
        
        logger.info("Processing models from system info")
        models: List[str] = system_info["CheckpointLoaderSimple"]["input"]["required"][
            "ckpt_name"
        ][0]
        logger.info(f"Found {len(models)} models")
        
        for model in models:
            logger.debug(f"Processing model: {model}")
            if model.startswith("sd-1.5\\"):
                sd_models.append(
                    OptionChoice(
                        model.replace("sd-1.5\\", "").replace(".safetensors", ""), model
                    )
                )
                sd_select_models.append(
                    SelectOption(
                        label=model.replace("sd-1.5\\", "").replace(".safetensors", ""),
                        value=model,
                    )
                )
            elif model.startswith("sdxl-1.0\\"):
                sdxl_models.append(
                    OptionChoice(
                        model.replace("sdxl-1.0\\", "").replace(".safetensors", ""), model
                    )
                )
                sdxl_select_models.append(
                    SelectOption(
                        label=model.replace("sdxl-1.0\\", "").replace(".safetensors", ""),
                        value=model,
                    )
                )
            else:
                logger.warning(f"Unknown model type for {model}")

        logger.info("Processing loras from system info")
        loras: List[str] = system_info["LoraLoader"]["input"]["required"]["lora_name"][0]
        logger.info(f"Found {len(loras)} loras")
        
        for lora in loras:
            logger.debug(f"Processing lora: {lora}")
            if lora.startswith("sd-1.5\\"):
                sd_loras.append(
                    OptionChoice(
                        lora.replace("sd-1.5\\", "").replace(".safetensors", ""), lora
                    )
                )
            elif lora.startswith("sdxl-1.0\\"):
                sdxl_loras.append(
                    OptionChoice(
                        lora.replace("sdxl-1.0\\", "").replace(".safetensors", ""), lora
                    )
                )
            else:
                logger.warning(f"Unknown lora type for {lora}")

        logger.info("Processing samplers and schedulers")
        system_samplers: List[str] = system_info["KSampler"]["input"]["required"]["sampler_name"][0]
        samplers.extend(OptionChoice(sampler, sampler) for sampler in system_samplers)
        logger.info(f"Found {len(system_samplers)} samplers")

        system_scheduler: List[str] = system_info["KSampler"]["input"]["required"]["scheduler"][0]
        schedulers.extend(OptionChoice(scheduler, scheduler) for scheduler in system_scheduler)
        logger.info(f"Found {len(system_scheduler)} schedulers")

        upscale_methods: List[str] = system_info["LatentUpscale"]["input"]["required"]["upscale_method"][0]
        upscale_latent.extend(upscale_methods)
        logger.info(f"Found {len(upscale_methods)} upscale methods")

        logger.info(f"Settings loaded: {len(sd_models)} SD models, {len(sdxl_models)} SDXL models, {len(sd_loras)} SD loras, {len(sdxl_loras)} SDXL loras")
        
    except KeyError as e:
        logger.error(f"Missing key in system_info: {e}")
        logger.error(f"Available keys: {list(system_info.keys())}")
        raise
    except Exception as e:
        logger.error(f"Error processing system info: {e}")
        raise
