import discord
from api.job_db import get_job, add_fluxjob, get_fluxjob, add_videojob, get_videojob, add_editjob, get_editjob
from dispatchers.dream_dispatcher import dream_dispatcher
from dispatchers.upscale_dispatcher import upscale_dispatcher
from settings import sdxl_select_models, sd_select_models
from models.sd_options import SDOptions
import random
import re
import io
import replicate
from io import BytesIO
from utils.logging_config import get_logger
from utils.error_utils import handle_interaction_error
from actions.base_job import ReplicateJob

logger = get_logger(__name__)


class BaseView(discord.ui.View):
    """Base view class with error handling for all UI interactions"""

    async def on_error(self, error: Exception, item: discord.ui.Item, interaction: discord.Interaction) -> None:
        """Handle errors that occur in view interactions"""
        await handle_interaction_error(
            error=error,
            interaction=interaction,
            context_type="view",
            context_name=self.__class__.__name__,
            custom_id=getattr(item, 'custom_id', 'unknown')
        )


class BaseModal(discord.ui.Modal):
    """Base modal class with error handling"""

    async def on_error(self, error: Exception, interaction: discord.Interaction) -> None:
        """Handle errors that occur in modal interactions"""
        await handle_interaction_error(
            error=error,
            interaction=interaction,
            context_type="modal",
            context_name=self.__class__.__name__,
            custom_id="N/A"
        )


# View used for SD drawing
class ComfySDView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(RedrawButton(self, "sd_button_redraw"))
        self.add_item(EditButton(self, "sd_button_edit"))
        self.add_item(EditImageButton(self, "sd_button_edit_image"))
        self.add_item(VideoButton(self, "sd_button_video"))
        self.add_item(SpoilerButton(self, "sd_button_spoiler"))
        self.add_item(UpscaleButton(self, "sd_button_upscale"))
        self.add_item(DeleteButton(self, "sd_button_delete"))
        self.add_item(ModelSelect(sd_select_models, self, "sd_model_select"))


# View used for SDXL drawing
class ComfySDXLView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RedrawButton(self, "sdxl_button_redraw"))
        self.add_item(EditButton(self, "sdxl_button_edit"))
        self.add_item(EditImageButton(self, "sdxl_button_edit_image"))
        self.add_item(VideoButton(self, "sdxl_button_video"))
        self.add_item(SpoilerButton(self, "sdxl_button_spoiler"))
        self.add_item(UpscaleButton(self, "sdxl_button_upscale"))
        self.add_item(DeleteButton(self, "sdxl_button_delete"))
        self.add_item(ModelSelect(sdxl_select_models, self, "sdxl_model_select"))


# View used for Flux drawing
class FluxView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(FluxEditButton(self, "flux_button_edit"))
        self.add_item(SpoilerButton(self, "flux_button_spoiler"))
        self.add_item(DeleteButton(self, "flux_button_delete"))

# View used for video generation
class VideoView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SpoilerButton(self, "video_button_spoiler"))
        self.add_item(DeleteButton(self, "video_button_delete"))

# View used for edit images
class EditView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(EditImageButton(self, "edit_button_edit_image"))
        self.add_item(VideoButton(self, "edit_button_video"))
        self.add_item(SpoilerButton(self, "edit_button_spoiler"))
        self.add_item(DeleteButton(self, "edit_button_delete"))



# View used for upscale
class UpscaleView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SpoilerButton(self, "upscale_button_spoiler"))
        self.add_item(DeleteButton(self, "upscale_button_delete"))


# Edit modal used when clicking one of the pen buttons.
class EditModal(BaseModal):
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

class ServerPromptModal(BaseModal):
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


class UserPromptModal(BaseModal):
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


class FluxPromptModal(BaseModal):
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

        # Create a task function for the replicate call
        async def flux_task():
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
            return output

        # Create and run the job
        job = ReplicateJob(flux_task)
        output_files = await job.run()

        job_id = add_fluxjob(prompt)
        await followup.delete()
        files = []
        for idx, output_file in enumerate(output_files):
            files.append(
                discord.File(
                    fp=io.BytesIO(await output_file.aread()),
                    filename=f"output-{idx}.png")
                )
        message_lines = [
            f"{interaction.user.mention} here is your image!",
            "```",
            f"{prompt[:1000] + (prompt[1000:] and '...')}",
            "```",
            f"Job ID ``{job_id}``"
        ]

        await interaction.channel.send(
            "\n".join(message_lines),
            files=files,
            view=FluxView()
        )

class VideoPromptModal(BaseModal):
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

        # Capture variables for the closure
        image = self.image
        resolution = self.resolution
        orientation = self.orientation

        # Create a task function for the replicate call
        async def video_task():
            if image:
                image_bytes = await image.read()
                output = await replicate.async_run(
                    "wan-video/wan-2.2-i2v-fast",
                    input={
                        "image": BytesIO(image_bytes),
                        "prompt": prompt,
                        "num_frames": 81,
                        "resolution": resolution
                    }
                )
            else:
                output = await replicate.async_run(
                    "wan-video/wan-2.2-t2v-fast",
                    input={
                        "prompt": prompt,
                        "num_frames": 81,
                        "resolution": resolution,
                        "aspect_ratio": "16:9" if orientation == "landscape"  else "9:16",
                    }
                )
            return output

        # Create and run the job
        job_id = add_videojob(prompt)
        job = ReplicateJob(video_task)
        output_file = await job.run()

        await followup.delete()
        files = []
        files.append(
            discord.File(
                fp=io.BytesIO(await output_file.aread()),
                filename=f"output.mp4")
            )

        message_lines = [
            f"{interaction.user.mention} here is your video!",
            "```",
            f"{prompt[:1000] + (prompt[1000:] and '...')}",
            "```",
            f"Job ID ``{job_id}``"
        ]

        await interaction.channel.send(
            "\n".join(message_lines),
            files=files,
            view=VideoView()
        )

class EditPromptModal(BaseModal):
    def __init__(self, image: discord.Attachment) -> None:
        super().__init__(title="Edit Image")
        self.image = image

        self.add_item(
            discord.ui.InputText(
                label="What do you want changed?",
                value="",
                required=True,
                max_length=4000,
                style=discord.InputTextStyle.long,
            )
        )

    async def callback(self, interaction):
        await interaction.response.defer()

        prompt = self.children[0].value
        followup = await interaction.followup.send("Request queued. Please Wait.")

        # Capture variables for the closure
        image = self.image

        # Create a task function for the replicate call
        async def edit_task():
            image_bytes = await image.read()
            output = await replicate.async_run(
                "google/nano-banana",
                input={
                    "prompt": prompt,
                    "image_input": [BytesIO(image_bytes)],
                    "output_format": "png"
                }
            )
            return output

        # Create and run the job
        job_id = add_editjob(prompt, image.url)
        job = ReplicateJob(edit_task)
        output_file = await job.run()

        logger.info(output_file.url)

        await followup.delete()
        files = []
        files.append(
            discord.File(
                fp=io.BytesIO(await output_file.aread()),
                filename=f"edited-output.png")
            )

        message_lines = [
            f"{interaction.user.mention} here is your edited image!",
            "```",
            f"{prompt[:1000] + (prompt[1000:] and '...')}",
            "```",
            f"Job ID ``{job_id}``"
        ]

        await interaction.channel.send(
            "\n".join(message_lines),
            files=files,
            view=EditView()
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

class VideoButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🎥")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            VideoPromptModal("", interaction.message.attachments[0], "480p", None)
        )

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

class EditImageButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🔧")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            EditPromptModal(interaction.message.attachments[0])
        )

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

class SpoilerButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🕵️")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        logger.debug(f"Spoiler interaction user: {interaction.message.mentions[0]}")
        logger.debug(f"Same user check: {interaction.message.mentions[0] == interaction.user}")
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
