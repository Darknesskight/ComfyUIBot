from discord.ext import commands
import discord
from settings import (
    sd_models,
    sdxl_models,
    sd_loras,
    sdxl_loras,
)
from .comfy_options import draw_options, default_options
from api.model_db import upsert_model_default, upsert_sd_default, init_model_db
from models.sd_options import SDType, SDOptions
from cogs.view import ComfySDView, ComfySDXLView
from dispatchers.dream_dispatcher import dream_dispatcher


class ComfyCog(commands.Cog, name="Stable Diffusion", description="Create images."):
    draw = discord.SlashCommandGroup(name="draw", description="Create an image")
    defaults = discord.SlashCommandGroup(name="defaults", description="Set defaults")

    @draw.command(name="sd", description="Create an image using Stable Diffusion 1.5")
    @draw_options(sd_models, sd_loras)
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
        sampler,
        scheduler,
        lora,
        lora_two,
        lora_three,
        hires,
        hires_strength,
    ):
        await ctx.response.defer()

        sd_options = await SDOptions.create(
            sd_type=SDType.SD,
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            width=width,
            height=height,
            steps=steps,
            seed=seed,
            cfg=cfg,
            sampler=sampler,
            scheduler=scheduler,
            lora=lora,
            lora_two=lora_two,
            lora_three=lora_three,
            hires=hires,
            hires_strength=hires_strength
        )
        await dream_dispatcher(sd_options, ctx.followup, ctx.channel, ctx.user, ComfySDView())
        
    @draw.command(
        name="sdxl", description="Create an image using Stable Diffusion XL 1.0"
    )
    @draw_options(sdxl_models, sdxl_loras)
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
        sampler,
        scheduler,
        lora,
        lora_two,
        lora_three,
        hires,
        hires_strength,
    ):
        await ctx.response.defer()

        sd_options = await SDOptions.create(
            sd_type=SDType.SDXL,
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            width=width,
            height=height,
            steps=steps,
            seed=seed,
            cfg=cfg,
            sampler=sampler,
            scheduler=scheduler,
            lora=lora,
            lora_two=lora_two,
            lora_three=lora_three,
            hires=hires,
            hires_strength=hires_strength
        )
        await dream_dispatcher(sd_options, ctx.followup, ctx.channel, ctx.user, ComfySDXLView())

    @defaults.command(
        name="sd", description="Set defaults for sd models"
    )
    @commands.is_owner()
    @default_options(sd_models)
    async def sd_defaults(
        self,
        ctx: discord.ApplicationContext,
        model: str,
        prompt_template,
        negative_prompt,
        width,
        height,
        steps,
        cfg,
        sampler,
        scheduler,
        hires,
        hires_strength,
    ):
        await ctx.response.defer(invisible=False)
        await upsert_sd_default(SDType.SD.value, model, prompt_template, negative_prompt, width, height, steps, cfg, sampler, scheduler, hires, hires_strength)
        await ctx.followup.send("Completed")

    @defaults.command(
        name="sdxl", description="Set defaults for sdxl models"
    )
    @commands.is_owner()
    @default_options(sdxl_models)
    async def sdxl_defaults(
        self,
        ctx: discord.ApplicationContext,
        model: str,
        prompt_template,
        negative_prompt,
        width,
        height,
        steps,
        cfg,
        sampler,
        scheduler,
        hires,
        hires_strength,
    ):
        await ctx.response.defer(invisible=False)
        await upsert_sd_default(SDType.SDXL.value, model, prompt_template, negative_prompt, width, height, steps, cfg, sampler, scheduler, hires, hires_strength)
        await ctx.followup.send("Completed")

    @defaults.command(
        name="model", description="Set defaults for a specific model"
    )
    @commands.is_owner()
    @default_options(sd_models + sdxl_models)
    async def model_defaults(
        self,
        ctx: discord.ApplicationContext,
        model: str,
        prompt_template,
        negative_prompt,
        width,
        height,
        steps,
        cfg,
        sampler,
        scheduler,
        hires,
        hires_strength,
    ):
        await ctx.response.defer(invisible=False)
        await upsert_model_default(model, prompt_template, negative_prompt, width, height, steps, cfg, sampler, scheduler, hires, hires_strength)
        await ctx.followup.send("Completed")

    @commands.Cog.listener()
    async def on_ready(self):
        await init_model_db()
