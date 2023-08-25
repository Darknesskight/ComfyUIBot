from discord.ext import commands
import discord
from settings import (
    sd_models,
    sdxl_models,
    sd_select_models,
    sdxl_select_models,
    default_sd_model,
    default_sdxl_model,
    default_sd_negs,
    default_sdxl_negs,
    templateEnv
)
from typing import Optional
from draw_job import DrawJob
from job_db import add_job, get_job
from comfy_options import draw_options
import textwrap
import random
import json
import io
import re
import math
import time

SDXL_1_0_TEMPLATE = "sdxl-1.0.j2"
SD_1_5_TEMPLATE = "sd-1.5.j2"


async def dream_handler(
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
        # now = time.time()

        # async def on_execution_start():
        #     print("no")

        # async def on_progress(value, max):
        #     progress = math.floor((value/max)*10)
        #     complete = '▓'*progress
        #     incomplete = '░' * (10-progress)
        #     print(msg.edited_at)
            
        #     await msg.edit(
        #         complete + incomplete
        #     )


        promptJson = json.loads(rendered_template)
        job = DrawJob(promptJson, ctx.followup)

        images, msg = await job.run()

        await msg.edit(
            "Drawing complete. Uploading now."
        )

        for node_id in images:
            for image_data in images[node_id]:
                file = discord.File(fp=io.BytesIO(image_data), filename="output.png")
                await ctx.channel.send(message, file=file, view=view)
                await msg.delete()

    except Exception as e:
        print(e)
        await ctx.followup.send(
            "Unable to create image. Please see log for details"
        )

class ComfyCog(commands.Cog, name="Stable Diffusion", description="Create images."):
    draw = discord.SlashCommandGroup(name="draw", description="Create an image")

    @draw.command(name="sd", description="Create an image using Stable Diffusion 1.5")
    @draw_options(default_sd_negs, default_sd_model, sd_models, 512, 512)
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
        glitch,
    ):
        await dream_handler(
            ctx,
            SD_1_5_TEMPLATE if not glitch else SDXL_1_0_TEMPLATE,
            ComfySDView(),
            prompt,
            negative_prompt,
            model,
            width,
            height,
            steps,
            seed,
            cfg,
        )

    @draw.command(
        name="sdxl", description="Create an image using Stable Diffusion XL 1.0"
    )
    @draw_options(default_sdxl_negs, default_sdxl_model, sdxl_models, 1024, 1024)
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
        glitch: Optional[bool] = None,
    ):
        await dream_handler(
            ctx,
            SDXL_1_0_TEMPLATE if not glitch else SD_1_5_TEMPLATE,
            ComfySDXLView(),
            prompt,
            negative_prompt,
            model,
            width,
            height,
            steps,
            seed,
            cfg,
        )


# creating the view that holds the buttons for /draw output
class ComfySDView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(RedrawButton(self, "sd_button_redraw"))
        self.add_item(EditButton(self, "sd_button_edit"))
        self.add_item(
            ModelSelect(sd_select_models, self, "sd_model_select")
        )


# creating the view that holds the buttons for /draw output
class ComfySDXLView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RedrawButton(self, "sdxl_button_redraw"))
        self.add_item(EditButton(self, "sdxl_button_edit"))
        self.add_item(
            ModelSelect(sdxl_select_models, self, "sdxl_model_select")
        )



class EditModal(discord.ui.Modal):
    def __init__(self, job_data, parent_view) -> None:
        super().__init__(title="Edit Prompt")
        self.job_data = job_data
        self.parent_view = parent_view

        self.add_item(
            discord.ui.InputText(
                label='New prompt',
                value=job_data["prompt"],
                style=discord.InputTextStyle.long
            )
        )
        self.add_item(
            discord.ui.InputText(
                label='New negative prompt',
                value=job_data["negative_prompt"],
                style=discord.InputTextStyle.long,
                required=False
            )
        )

    async def callback(self, interaction: discord.Interaction):
        self.job_data["prompt"] = self.children[0].value
        self.job_data["negative_prompt"] = self.children[1].value

        await dream_handler(
            **self.job_data,
            view=self.parent_view,
            ctx=interaction
        )


class ModelSelect(discord.ui.Select):
    def __init__(self, models, parent_view, custom_id):
        super().__init__(placeholder="Select model to redraw with", options=models, custom_id=custom_id)
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        job_id_search = re.search('Job ID ``(\d+)``$', interaction.message.content, re.IGNORECASE)
        job_id = job_id_search.group(1)
        
        job_data = get_job(job_id)
        job_data["model"] = self.values[0]
        
        await dream_handler(
            **job_data,
            view=self.parent_view,
            ctx=interaction,
        )

class EditButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🖋")
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        job_id_search = re.search('Job ID ``(\d+)``$', interaction.message.content, re.IGNORECASE)
        job_id = job_id_search.group(1)
        
        job_data = get_job(job_id)
        await interaction.response.send_modal(EditModal(job_data, self.parent_view))

class RedrawButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🎲")
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        job_id_search = re.search('Job ID ``(\d+)``$', interaction.message.content, re.IGNORECASE)
        job_id = job_id_search.group(1)
        
        job_data = get_job(job_id)
        job_data["seed"] = None
        
        await dream_handler(
            **job_data,
            view=self.parent_view,
            ctx=interaction
        )