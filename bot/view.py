import discord
from api.job_db import get_job
from settings import sdxl_select_models, sd_select_models
from actions.dream import dream
from actions.upscale import upscale
from actions.glitch import glitch
import re
import io


# View used for SD drawing
class ComfySDView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(RedrawButton(self, "sd_button_redraw"))
        self.add_item(EditButton(self, "sd_button_edit"))
        self.add_item(SpoilorButton(self, "sd_button_spoiler"))
        self.add_item(UpscaleButton(self, "sd_button_upscale"))
        self.add_item(DeleteButton(self, "sd_button_delete"))
        self.add_item(GlitchButton(self, "sd_button_glitch"))
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
        self.add_item(GlitchButton(self, "sdxl_button_glitch"))
        self.add_item(ModelSelect(sdxl_select_models, self, "sdxl_model_select"))


# View used for upscale
class UpscaleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SpoilorButton(self, "upscale_button_spoiler"))
        self.add_item(DeleteButton(self, "upscale_button_delete"))


# Edit modal used when clicking one of the pen buttons.
class EditModal(discord.ui.Modal):
    def __init__(self, job_data, parent_view) -> None:
        super().__init__(title="Edit Prompt")
        self.job_data = job_data
        self.parent_view = parent_view

        self.add_item(
            discord.ui.InputText(
                label="New prompt",
                value=job_data["prompt"],
                style=discord.InputTextStyle.long,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="New negative prompt",
                value=job_data["negative_prompt"],
                style=discord.InputTextStyle.long,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        self.job_data["prompt"] = self.children[0].value
        self.job_data["negative_prompt"] = self.children[1].value

        await dream(**self.job_data, view=self.parent_view, ctx=interaction)


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
        job_id_search = re.findall(
            "Job ID ``(\d+)``", interaction.message.content, re.IGNORECASE
        )
        job_id = job_id_search[-1]

        job_data = get_job(job_id)
        job_data["model"] = self.values[0]

        await dream(
            **job_data,
            view=self.parent_view,
            ctx=interaction,
        )


class EditButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🖋")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        job_id_search = re.findall(
            "Job ID ``(\d+)``", interaction.message.content, re.IGNORECASE
        )
        job_id = job_id_search[-1]

        job_data = get_job(job_id)
        await interaction.response.send_modal(EditModal(job_data, self.parent_view))


class RedrawButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🎲")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        job_id_search = re.findall(
            "Job ID ``(\d+)``", interaction.message.content, re.IGNORECASE
        )
        job_id = job_id_search[-1]

        job_data = get_job(job_id)
        job_data["seed"] = None

        await dream(**job_data, view=self.parent_view, ctx=interaction)


class SpoilorButton(discord.ui.Button):
    def __init__(self, parent_view, custom_id):
        super().__init__(custom_id=custom_id, emoji="🕵️")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        print(interaction.message.mentions[0])
        print(interaction.message.mentions[0] == interaction.user)
        message = interaction.message.content
        await interaction.message.edit(
            message + "\n# Converting message to spoiler", attachments=[]
        )

        files = []
        for attachment in interaction.message.attachments:
            file = await attachment.read()
            files.append(
                discord.File(fp=io.BytesIO(file), filename="output.png", spoiler=True)
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
        attachments = interaction.message.attachments
        if len(attachments) != 1:
            await interaction.followup.send("Unable to upscale image.")
            return

        await upscale(interaction, attachments[0], UpscaleView())


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
