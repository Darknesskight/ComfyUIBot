import time
import math
import discord
import textwrap


class ProgressMessenger:
    last_update = time.time()
    last_sent_image = None

    def __init__(self, channel):
        self.channel = channel
        self.channel_message = None

    async def on_progress(self, percentage, image):
            if time.time() - self.last_update >= 0.5:
                files = []
                if self.last_sent_image and self.last_sent_image != image:
                    files.append(discord.File(image, filename="progress.jpg"))

                if self.channel_message is None:
                    self.channel_message = await self.channel.send(self.format_progress(percentage), files=files)
                else:
                    await self.channel_message.edit(content=self.format_progress(percentage), files=files)
                self.last_update = time.time()
                self.last_sent_image = image

    def format_progress(self, percentage):
        progress = math.floor(percentage * 10)
        complete = "▓" * progress
        incomplete = "░" * (10 - progress)
        return complete + incomplete

    async def on_complete(self, message):
            if self.channel_message is None:
                self.channel_message = await self.channel.send(message, wait=True)
            else:
                await self.channel_message.edit(message)

    async def delete_message(self):
         if self.channel_message:
             await self.channel_message.delete()

def format_image_message(user, sd_options, job_id):
     return textwrap.dedent(
          f"""\
                {user.mention} here is your image!
                Prompt: ``{sd_options.prompt}``
                Model ``{sd_options.model}``
                CFG ``{sd_options.cfg}`` - Steps: ``{sd_options.steps}`` - Seed ``{sd_options.seed}``
                Size ``{sd_options.width}``x``{sd_options.height}`` Job ID ``{job_id}``
          """)