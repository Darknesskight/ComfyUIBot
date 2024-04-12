import time
import math
import discord


class ProgressMessage:
    last_update = time.time()
    msg = None
    image = None
    last_sent_image = None

    def __init__(self, followup):
        super().__init__()
        self.followup = followup

    async def send_progress(self, percentage):
        if time.time() - self.last_update >= 0.5:
            progress = math.floor(percentage * 10)
            complete = "▓" * progress
            incomplete = "░" * (10 - progress)
            await self.send_message(complete + incomplete)
            self.last_update = time.time()

    async def send_message(self, message):
        files = []
        if self.image and self.image != self.last_sent_image:
            files.append(discord.File(self.image, filename="progress.jpg"))
        if not self.msg:
            self.msg = await self.followup.send(message, files=files, wait=True)
        else:
            await self.msg.edit(message, files=files)

        # Cache what we sent last so we don't resend the same image.
        self.last_sent_image = self.image

    async def delete_message(self):
        if self.msg:
            await self.msg.delete()
