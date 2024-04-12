import asyncio
from discord import Message, Bot
from api.openai_api import send_message
from api.tea_db import get_channel_ids, is_user_opt_out
from actions.dream import tea_dream
from settings import (
    default_sdxl_model,
    default_sdxl_negs,
    sdxl_template,
    default_steps,
    default_cfg,
)
from bot.view import ComfySDXLView
from PIL import Image
import base64
import io

MAX_LENGTH = 1500


class TeaCogMessageQueue:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.message_queue: asyncio.Queue[Message] = asyncio.Queue()
        self.image_queue: asyncio.Queue[tuple[str, Message]] = asyncio.Queue()
        bot.loop.create_task(self._process_message_queue())
        bot.loop.create_task(self._process_image_queue())

    async def queue_message(self, message: Message):
        await self.message_queue.put(message)

    async def queue_image(self, prompt: str, message: Message):
        await self.image_queue.put(prompt, message)

    async def _process_message_queue(self):
        while True:
            try:
                message = await self.message_queue.get()
                b64_image: str = None
                for attachment in message.attachments:
                    if "image" in attachment.content_type:
                        b64_image = self._get_message_image(await attachment.read())
                        break

                if await self._should_process_message(message):
                    async with message.channel.typing():
                        username = str(message.author.display_name)
                        formatted_message = f"{username}: {message.clean_content}"
                        response = self._remove_username_prefix(
                            await send_message(
                                message.guild.id,
                                message.author.id,
                                username,
                                formatted_message,
                                b64_image,
                            ),
                            username,
                        )
                        parsed_response = response.split("IMAGE:")
                        if len(parsed_response) > 1:
                            prompt = parsed_response[1]
                            await self.image_queue.put((prompt, message))
                        if parsed_response[0].strip():
                            await self._send_response(
                                message.channel,
                                self._remove_username_prefix(
                                    parsed_response[0], username
                                ),
                            )
            finally:
                self.message_queue.task_done()  # signals that the message has been processed

    async def _process_image_queue(self):
        while True:
            try:
                prompt, message = await self.image_queue.get()
                await tea_dream(
                    message,
                    sdxl_template,
                    ComfySDXLView(),
                    prompt,
                    default_sdxl_negs,
                    default_sdxl_model,
                    1024,
                    1024,
                    default_steps,
                    None,
                    default_cfg,
                )
            finally:
                self.image_queue.task_done()  # signals that the message has been processed

    async def _should_process_message(self, message: Message):
        channel_ids = await get_channel_ids(message.guild.id)
        user_opted_out = await is_user_opt_out(message.author.name)
        allowed_channel = message.channel.id in channel_ids
        was_mentioned = (
            self.bot.user.mentioned_in(message) and not message.mention_everyone
        )
        return (allowed_channel or was_mentioned) and not user_opted_out

    def _remove_username_prefix(self, response: str, username: str) -> str:
        username_lower = username.lower()
        response_start = response[: len(username) + 2].lower()
        if response_start.startswith((username_lower + ". ", username_lower + ": ")):
            response = response[len(username) + 2 :]
        return response

    async def _send_response(self, channel, response):
        if len(response) > MAX_LENGTH:
            for i in range(0, len(response), MAX_LENGTH):
                await channel.send(response[i : i + MAX_LENGTH])
        else:
            await channel.send(response)

    def _get_message_image(self, image: bytes) -> str:
        # Download the image
        if not image:
            return None

        with io.BytesIO(image) as image_io:
            image = Image.open(image_io)
            if image.size[0] > 768 or image.size[1] > 2000:
                image.thumbnail((768, 2000))
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")

            compressed_io = io.BytesIO()
            for quality in range(100, 0, -5):
                compressed_io.seek(0)
                image.save(compressed_io, format="JPEG", quality=quality, optimize=True)
                size = compressed_io.tell()
                if size < 20 * 1024 * 1024:
                    break

            if size >= 20 * 1024 * 1024:
                return None

            compressed_io.seek(0)
            image_base64 = base64.b64encode(compressed_io.getvalue())

            return image_base64.decode("utf-8")
