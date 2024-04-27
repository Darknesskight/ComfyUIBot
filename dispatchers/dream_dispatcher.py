import discord
from actions.dream import dream
from models.sd_options import SDOptions
from utils.message_utils import ProgressMessenger, format_image_message
from api.job_db import add_job

async def dream_dispatcher(sd_options: SDOptions, followup, channel, user, view):
    progress_messenger = ProgressMessenger(channel)
    job_id = add_job(sd_options)

    if followup:
        await followup.send("Request queued. Please Wait.", delete_after=10)
    
    image = await dream(sd_options, progress_messenger.on_progress)
    await progress_messenger.on_complete("Drawing Complete. Uploading now.") 
    image_file = discord.File(fp=image, filename="output.png")
    await channel.send(
        format_image_message(user, sd_options, job_id),
        file=image_file, view=view
    )
    await progress_messenger.delete_message()