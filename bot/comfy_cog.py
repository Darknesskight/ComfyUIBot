from discord.ext import commands
import discord
from settings import (
    sd_models,
    sdxl_models,
    sd_loras,
    sdxl_loras,
    default_sd_model,
    default_sdxl_model,
    default_sd_negs,
    default_sdxl_negs,
    sd_template,
    sdxl_template,
)
from typing import Optional
from bot.comfy_options import draw_options
from actions.dream import dream
from bot.view import ComfySDView, ComfySDXLView


class ComfyCog(commands.Cog, name="Stable Diffusion", description="Create images."):
    draw = discord.SlashCommandGroup(name="draw", description="Create an image")

    @draw.command(name="sd", description="Create an image using Stable Diffusion 1.5")
    @draw_options(
        default_sd_negs,
        default_sd_model,
        sd_models,
        1024,
        1024,
        sd_loras,
        "nearest-exact",
    )
    async def dream_sd(
        self,
        ctx: discord.ApplicationContext,
        prompt: str,
        negative_prompt,
        model,
        width,
        height,
        steps,
        seed,
        cfg,
        lora,
        lora_two,
        lora_three,
        hires,
        hires_strength,
        glitch,
    ):
        await dream(
            ctx,
            sd_template if not glitch else sdxl_template,
            ComfySDView(),
            prompt,
            negative_prompt,
            model,
            width,
            height,
            steps,
            seed,
            cfg,
            lora,
            lora_two,
            lora_three,
            hires,
            hires_strength,
        )

    @draw.command(
        name="sdxl", description="Create an image using Stable Diffusion XL 1.0"
    )
    @draw_options(
        default_sdxl_negs, default_sdxl_model, sdxl_models, 1024, 1024, sdxl_loras, None
    )
    async def dream_sdxl(
        self,
        ctx: discord.ApplicationContext,
        prompt: str,
        negative_prompt,
        model,
        width,
        height,
        steps,
        seed,
        cfg,
        lora,
        lora_two,
        lora_three,
        hires,
        hires_strength,
        glitch,
    ):
        await dream(
            ctx,
            sdxl_template if not glitch else sd_template,
            ComfySDXLView(),
            prompt,
            negative_prompt,
            model,
            width,
            height,
            steps,
            seed,
            cfg,
            lora,
            lora_two,
            lora_three,
            hires,
            hires_strength,
        )
