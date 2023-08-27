import discord
from api.job_db import get_job
from settings import sdxl_select_models, sd_select_models, sd_select_loras
from actions.dream import dream
import re

# View used for SD drawing
class ComfySDView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(RedrawButton(self, "sd_button_redraw"))
        self.add_item(EditButton(self, "sd_button_edit"))
        self.add_item(
            ModelSelect(sd_select_models, self, "sd_model_select")
        )


# View used for SDXL drawing
class ComfySDXLView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RedrawButton(self, "sdxl_button_redraw"))
        self.add_item(EditButton(self, "sdxl_button_edit"))
        self.add_item(
            ModelSelect(sdxl_select_models, self, "sdxl_model_select")
        )

# Edit modal used when clicking one of the pen buttons.
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

        await dream(
            **self.job_data,
            view=self.parent_view,
            ctx=interaction
        )


# Select dropdown for models.
class ModelSelect(discord.ui.Select):
    def __init__(self, models, parent_view, custom_id):
        super().__init__(placeholder="Select model to redraw with", options=models, custom_id=custom_id)
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        job_id_search = re.search('Job ID ``(\d+)``$', interaction.message.content, re.IGNORECASE)
        job_id = job_id_search.group(1)
        
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
        
        await dream(
            **job_data,
            view=self.parent_view,
            ctx=interaction
        )
