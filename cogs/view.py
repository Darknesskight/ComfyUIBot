import discord
from api.job_db import get_job, add_fluxjob, get_fluxjob, add_videojob, get_videojob
from dispatchers.dream_dispatcher import dream_dispatcher
from dispatchers.upscale_dispatcher import upscale_dispatcher
from settings import sdxl_select_models, sd_select_models
from actions.upscale import upscale
from actions.glitch import glitch
from models.sd_options import SDOptions
import random
import re
import io
import replicate
import urllib.request
import textwrap
from io import BytesIO


# View used for SD drawing
class ComfySDView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(RedrawButton(self, "sd_button_redraw"))
        self.add_item(EditButton(self, "sd_button_edit"))
        self.add_item(SpoilorButton(self, "sd_button_spoiler"))
        self.add_item(UpscaleButton(self, "sd_button_upscale"))
        self.add_item(DeleteButton(self, "sd_button_delete"))
        # self.add_item(GlitchButton(self, "sd_button_glitch"))
        self.add_item(ModelSelect(sd_select_models, self, "sd_model_select"))


# View used for SDXL drawing
class ComfySDXLView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RedrawButton(self, "sdxl_button_redraw"))
        self.add_item(EditButton(self, "sdxl_button_edit"))
        self.add_item(SpoilorButton(self, "sdxl_button_spoiler"))
        self.add_item(UpscaleButton(self, "sdxl_button_upscale"))
        self.add_item(DeleteButton(self, "sdxl_button_delete"))
        # self.add_item(GlitchButton(self, "sdxl_button_glitch"))
        self.add_item(ModelSelect(sdxl_select_models, self, "sdxl_model_select"))


# View used for SDXL drawing
class FluxView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(FluxEditButton(self, "flux_button_edit"))
        self.add_item(SpoilorButton(self, "flux_button_spoiler"))
        self.add_item(DeleteButton(self, "flux_button_delete"))

# View used for SDXL drawing
class VideoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SpoilorButton(self, "video_button_spoiler"))
        self.add_item(DeleteButton(self, "video_button_delete"))



# View used for upscale
class UpscaleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SpoilorButton(self, "upscale_button_spoiler"))
        self.add_item(DeleteButton(self, "upscale_button_delete"))


# Edit modal used when clicking one of the pen buttons.
class EditModal(discord.ui.Modal):
    def __init__(self, sd_options: SDOptions, parent_view) -> None:
        super().__init__(title="Edit Prompt")
        self.sd_options = sd_options
        self.parent_view = parent_view

        self.add_item(
            discord.ui.InputText(
                label="New prompt",
                value=sd_options.prompt,
                style=discord.InputTextStyle.long,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="New negative prompt",
                value=sd_options.negative_prompt,
                style=discord.InputTextStyle.long,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.sd_options.prompt = self.children[0].value
        self.sd_options.negative_prompt = self.children[1].value
        await dream_dispatcher(self.sd_options, interaction.followup, interaction.channel, interaction.user, self.parent_view)

class ServerPromptModal(discord.ui.Modal):
    def __init__(self, server_prompt, on_submit) -> None:
        super().__init__(title="Server Prompt")
        self.server_prompt = server_prompt
        self.on_submit = on_submit

        self.add_item(
            discord.ui.InputText(
                label="New prompt",
                value=server_prompt or "",
                required=False,
                style=discord.InputTextStyle.long,
            )
        )

    async def callback(self, interaction):
        await self.on_submit(self.children[0].value)
        await interaction.response.send_message("Server prompt updated.")


class UserPromptModal(discord.ui.Modal):
    def __init__(self, user_prompt, on_submit) -> None:
        super().__init__(title="User Prompt")
        self.user_prompt = user_prompt
        self.on_submit = on_submit

        self.add_item(
            discord.ui.InputText(
                label="New prompt",
                value=user_prompt or "",
                required=False,
                max_length=1000,
                style=discord.InputTextStyle.long,
            )
        )

    async def callback(self, interaction):
        await self.on_submit(self.children[0].value)
        await interaction.response.send_message("User prompt updated.")


class FluxPromptModal(discord.ui.Modal):
    def __init__(self, prompt) -> None:
        super().__init__(title="Prompt")
        self.prompt = prompt

        self.add_item(
            discord.ui.InputText(
                label="Prompt",
                value=prompt or "",
                required=False,
                max_length=4000,
                style=discord.InputTextStyle.long,
            )
        )

    async def callback(self, interaction):
        await interaction.response.defer()

        prompt = self.children[0].value
        followup = await interaction.followup.send("Request queued. Please Wait.")
        output = await replicate.async_run(
            "black-forest-labs/flux-dev",
            input={
                "prompt": prompt,
                "guidance": 3.5,
                "num_outputs": 2,
                "aspect_ratio": "1:1",
                "output_format": "webp",
                "output_quality": 100,
                "prompt_strength": 1,
                "num_inference_steps": 30,
                "disable_safety_checker": True
            }
        )
        job_id = add_fluxjob(prompt)
        await followup.delete()
        files = []
        for idx, url in enumerate(output):
            with urllib.request.urlopen(url) as response:
                files.append(
                    discord.File(
                        fp=io.BytesIO(response.read()),
                        filename=f"output-{idx}.png")
                    )

        await interaction.channel.send(
            textwrap.dedent(
                f"""\
{interaction.user.mention} here is your image!
```
{prompt[:1000] + (prompt[1000:] and '...')}
```
Job ID ``{job_id}``
                """),
            files=files,
            view=FluxView()
        )

class VideoPromptModal(discord.ui.Modal):
    def __init__(self, prompt, image: discord.Attachment, resolution: str, orientation: str) -> None:
        super().__init__(title="Prompt")
        self.prompt = prompt
        self.image = image
        self.resolution = resolution
        self.orientation = orientation

        self.add_item(
            discord.ui.InputText(
                label="Prompt",
                value=prompt or "",
                required=False,
                max_length=4000,
                style=discord.InputTextStyle.long,
            )
        )

    async def callback(self, interaction):
        await interaction.response.defer()

        prompt = self.children[0].value
        followup = await interaction.followup.send("Request queued. Please Wait.")
        if self.image:
            image_bytes = await self.image.read()
            model = "wavespeedai/wan-2.1-i2v-720p" if self.resolution == "720p" else "wavespeedai/wan-2.1-i2v-480p"
            max_area_map = {
                ("720p", "portrait"): "720x1280",
                ("720p", "landscape"): "1280x720",
                ("480p", "portrait"): "480x832",
                ("480p", "landscape"): "832x480",
            }
            max_area = max_area_map[(self.resolution, self.orientation)]
            print(self.resolution)
            print(self.orientation)
            print(model)
            print(max_area)
            output = await replicate.async_run(
                model,
                input={
                    "image": BytesIO(image_bytes),
                    "prompt": prompt,
                    "max_area": max_area,
                    "fast_mode": "Balanced",
                    "lora_scale": 1,
                    "num_frames": 81,
                    "sample_shift": 5,
                    "sample_steps": 30,
                    "frames_per_second": 16,
                    "sample_guide_scale": 5
                }
            )
        else:
            output = await replicate.async_run(
                "wavespeedai/wan-2.1-t2v-480p",
                input={
                    "prompt": prompt,
                    "fast_mode": "Balanced",
                    "num_frames": 81,
                    "aspect_ratio": "16:9",
                    "sample_shift": 5,
                    "sample_steps": 30,
                    "frames_per_second": 16,
                    "sample_guide_scale": 5
                }
            )
        job_id = add_videojob(prompt)
        await followup.delete()
        files = []
        with urllib.request.urlopen(output) as response:
            files.append(
                discord.File(
                    fp=io.BytesIO(response.read()),
                    filename=f"output.mp4")
                )

        await interaction.channel.send(
            textwrap.dedent(
                f"""\
{interaction.user.mention} here is your video!
```
{prompt[:1000] + (prompt[1000:] and '...')}
```
Job ID ``{job_id}``
                """),
            files=files,
            view=VideoView()
        )


# Select dropdown for models.
class ModelSelect(discord.ui.Select):
    def __init__(self, models, parent_view, custom_id):
        super().__init__(
            placeholder="Select model to redraw with",
            options=models,
            custom_id=custom_id,
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        job_id_search = re.findall(
            "Job ID ``(\d+)``", interaction.message.content, re.IGNORECASE
        )
        job_id = job_id_search[-1]

        sd_options = get_job(job_id)
        sd_options.model = self.values[0]
        await dream_dispatcher(sd_options, interaction.followup, interaction.channel, interaction.user, self.parent_view)

class EditButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🖋")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        job_id_search = re.findall(
            "Job ID ``(\d+)``", interaction.message.content, re.IGNORECASE
        )
        job_id = job_id_search[-1]

        sd_options = get_job(job_id)
        await interaction.response.send_modal(EditModal(sd_options, self.parent_view))

class FluxEditButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🖋")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        job_id_search = re.findall(
            "Job ID ``(\d+)``", interaction.message.content, re.IGNORECASE
        )
        job_id = job_id_search[-1]

        prompt = get_fluxjob(job_id)
        await interaction.response.send_modal(FluxPromptModal(prompt))

class VideoEditButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🖋")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        job_id_search = re.findall(
            "Job ID ``(\d+)``", interaction.message.content, re.IGNORECASE
        )
        job_id = job_id_search[-1]

        prompt = get_videojob(job_id)
        await interaction.response.send_modal(VideoPromptModal(prompt))



class RedrawButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🎲")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        job_id_search = re.findall(
            "Job ID ``(\d+)``", interaction.message.content, re.IGNORECASE
        )
        job_id = job_id_search[-1]

        sd_options = get_job(job_id)
        sd_options.seed = random.randint(1, 4294967294)
        await dream_dispatcher(sd_options, interaction.followup, interaction.channel, interaction.user, self.parent_view)

class SpoilorButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🕵️")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        print(interaction.message.mentions[0])
        print(interaction.message.mentions[0] == interaction.user)
        message = interaction.message.content

        files = []
        for attachment in interaction.message.attachments:
            file = await attachment.read()
            files.append(
                discord.File(fp=io.BytesIO(file), filename="output.png", spoiler=True)
            )

        await interaction.message.edit(
            message + "\n# Converting message to spoiler", attachments=[]
        )

        await interaction.message.edit(
            message, files=files, view=self.parent_view, attachments=[]
        )

        await interaction.followup.send(
            "Image changed to spoiler", ephemeral=True, delete_after=3
        )


class DeleteButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="❌")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        has_manage_permission = interaction.channel.permissions_for(
            interaction.user
        ).manage_messages
        same_user = interaction.message.mentions[0] == interaction.user
        if has_manage_permission or same_user:
            await interaction.message.delete()
            await interaction.followup.send(
                "Image deleted", ephemeral=True, delete_after=3
            )
        else:
            await interaction.followup.send(
                "You do not have permission to remove this image",
                ephemeral=True,
                delete_after=3,
            )


class UpscaleButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="⬆️")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        attachments = interaction.message.attachments
        if len(attachments) != 1:
            await interaction.followup.send("Unable to upscale image.")
            return

        await upscale_dispatcher(attachments[0], interaction.followup, interaction.channel, interaction.user, UpscaleView())


class GlitchButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🦠")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        attachments = interaction.message.attachments
        if len(attachments) != 1:
            await interaction.followup.send("Unable to gltich image.")
            return

        await glitch(interaction, attachments[0], UpscaleView())
