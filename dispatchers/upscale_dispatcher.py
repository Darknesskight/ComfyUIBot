import discord
from actions.upscale import upscale
from utils.message_utils import ProgressMessenger

async def upscale_dispatcher(image, followup, channel, user, view):
    progress_messenger = ProgressMessenger(channel)

    if followup:
        await followup.send("Request queued. Please Wait.", delete_after=10)
    
    image = await upscale(image, progress_messenger.on_progress)
    await progress_messenger.on_complete("Upscaling Complete. Uploading now.") 
    image_file = discord.File(fp=image, filename="output.png")
    await channel.send(
        f"{user.mention} here is your upscaled image!",
        file=image_file, view=view
    )
    await progress_messenger.delete_message()