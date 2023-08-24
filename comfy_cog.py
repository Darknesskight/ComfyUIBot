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
)
from typing import Optional
from draw_job import DrawJob
from comfy_options import draw_options
import textwrap
import random
import json
import io
import jinja2
import re

SDXL_1_0_TEMPLATE = "sdxl-1.0.j2"
SD_1_5_TEMPLATE = "sd-1.5.j2"

templateLoader = jinja2.FileSystemLoader(searchpath="./templates")
templateEnv = jinja2.Environment(loader=templateLoader)


async def dream_handler(
    ctx: discord.ApplicationContext | discord.Interaction,
    template,
    comfy_api,
    comfy_websocket,
    job_db,
    prompt,
    negative_prompt,
    model,
    width,
    height,
    steps,
    seed,
    cfg,
):
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
    job_id = job_db.add_job(options)
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
    job = DrawJob(promptJson, comfy_api, comfy_websocket)
    return (await job.run(), message)


class ComfyCog(
    commands.Cog,
    name="Stable Diffusion",
    description="Create images from natural language.",
):
    draw = discord.SlashCommandGroup(name="draw", description="Create an image")

    def __init__(
        self, bot, settings, comfy_api, comfy_websocket, job_db
    ):
        self.bot = bot
        self.settings = settings
        self.comfy_api = comfy_api
        self.comfy_websocket = comfy_websocket
        self.job_db = job_db

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
        try:
            await self._deam(
                ctx,
                SD_1_5_TEMPLATE if not glitch else SDXL_1_0_TEMPLATE,
                ComfySDView(self.comfy_api, self.comfy_websocket, self.job_db),
                prompt,
                negative_prompt,
                model,
                width,
                height,
                steps,
                seed,
                cfg,
            )
        except Exception as e:
            print(e)
            await ctx.followup.send(
                "Unable to create image. Please see log for details"
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
        try:
            await self._deam(
                ctx,
                SDXL_1_0_TEMPLATE if not glitch else SD_1_5_TEMPLATE,
                ComfySDXLView(self.comfy_api, self.comfy_websocket, self.job_db),
                prompt,
                negative_prompt,
                model,
                width,
                height,
                steps,
                seed,
                cfg,
            )
        except Exception as e:
            print(e)
            await ctx.followup.send(
                "Unable to create image. Please see log for details"
            )

    async def _deam(
        self,
        ctx: discord.ApplicationContext,
        template,
        view,
        prompt: str,
        negative_prompt,
        model,
        width,
        height,
        steps,
        seed,
        cfg,
    ):
        await ctx.defer()
        images, message = await dream_handler(
            ctx,
            template,
            self.comfy_api,
            self.comfy_websocket,
            self.job_db,
            prompt,
            negative_prompt,
            model,
            width,
            height,
            steps,
            seed,
            cfg
        )
        for node_id in images:
            for image_data in images[node_id]:
                file = discord.File(fp=io.BytesIO(image_data), filename="output.png")
                msg = await ctx.send_followup(
                    "Drawing complete. Uploading now.", wait=True
                )
                await ctx.send(message, file=file, view=view)
                await msg.delete()

    async def cog_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        await ctx.followup.send("Unable to create image. Please see log for details")
        print(error)


# creating the view that holds the buttons for /draw output
class ComfySDView(discord.ui.View):
    def __init__(self, comfy_api, comfy_websocket, job_db):
        super().__init__(timeout=None)
        self.comfy_api = comfy_api
        self.comfy_websocket = comfy_websocket
        self.job_db = job_db
        self.add_item(RedrawButton(self, "sd_button_redraw"))
        self.add_item(EditButton(self, "sd_button_edit"))
        self.add_item(
            ModelSelect(sd_select_models, self, "sd_model_select")
        )


# creating the view that holds the buttons for /draw output
class ComfySDXLView(discord.ui.View):
    def __init__(self, comfy_api, comfy_websocket, job_db):
        super().__init__(timeout=None)
        self.comfy_api = comfy_api
        self.comfy_websocket = comfy_websocket
        self.job_db = job_db
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
        await interaction.response.defer(invisible=False)
        try:
            self.job_data["prompt"] = self.children[0].value
            self.job_data["negative_prompt"] = self.children[1].value

            (images, message) = await dream_handler(
                **self.job_data,
                ctx=interaction,
                comfy_api=self.parent_view.comfy_api,
                comfy_websocket=self.parent_view.comfy_websocket,
                job_db=self.parent_view.job_db
            )

            msg = await interaction.followup.send(
                "Drawing complete. Uploading now.", wait=True
            )

            for node_id in images:
                for image_data in images[node_id]:
                    file = discord.File(fp=io.BytesIO(image_data), filename="output.png")
                    await interaction.channel.send(message, file=file, view=self.parent_view)
                    await msg.delete()
        except Exception as e:
            print(e)
            await interaction.followup.send(
                "Unable to create image. Please see log for details"
            )


class ModelSelect(discord.ui.Select):
    def __init__(self, models, parent_view, custom_id):
        super().__init__(placeholder="Select model to redraw with", options=models, custom_id=custom_id)
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(invisible=False)
        try:
            
            job_id_search = re.search('Job ID ``(\d+)``$', interaction.message.content, re.IGNORECASE)
            job_id = job_id_search.group(1)
            
            job_data = self.parent_view.job_db.get_job(job_id)
            job_data["model"] = self.values[0]
            
            (images, message) = await dream_handler(
                **job_data,
                ctx=interaction,
                comfy_api=self.parent_view.comfy_api,
                comfy_websocket=self.parent_view.comfy_websocket,
                job_db=self.parent_view.job_db
            )

            msg = await interaction.followup.send(
                "Drawing complete. Uploading now.", wait=True
            )

            for node_id in images:
                for image_data in images[node_id]:
                    file = discord.File(fp=io.BytesIO(image_data), filename="output.png")
                    await interaction.channel.send(message, file=file, view=self.parent_view)
                    await msg.delete()
        except Exception as e:
            print(e)
            await interaction.followup.send(
                "Unable to create image. Please see log for details"
            )

class EditButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🖋")
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        try:
            job_id_search = re.search('Job ID ``(\d+)``$', interaction.message.content, re.IGNORECASE)
            job_id = job_id_search.group(1)
            
            job_data = self.parent_view.job_db.get_job(job_id)
            await interaction.response.send_modal(EditModal(job_data, self.parent_view))
        except Exception as e:
            print(e)
            await interaction.followup.send(
                "Unable to create image. Please see log for details"
            )

class RedrawButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🎲")
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(invisible=False)
        try:
            job_id_search = re.search('Job ID ``(\d+)``$', interaction.message.content, re.IGNORECASE)
            job_id = job_id_search.group(1)
            
            job_data = self.parent_view.job_db.get_job(job_id)
            job_data["seed"] = None
            
            (images, message) = await dream_handler(
                **job_data,
                ctx=interaction,
                comfy_api=self.parent_view.comfy_api,
                comfy_websocket=self.parent_view.comfy_websocket,
                job_db=self.parent_view.job_db
            )

            msg = await interaction.followup.send(
                "Drawing complete. Uploading now.", wait=True
            )

            for node_id in images:
                for image_data in images[node_id]:
                    file = discord.File(fp=io.BytesIO(image_data), filename="output.png")
                    await interaction.channel.send(message, file=file, view=self.parent_view)
                    await msg.delete()
        except Exception as e:
            print(e)
            await interaction.followup.send(
                "Unable to create image. Please see log for details"
            )