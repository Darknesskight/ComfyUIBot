import discord
import logging

from settings import bot_token, set_comfy_settings
from api.comfy_api import get_system_info
from api.comfy_websocket import wsrun
from api.job_db import init_db
from cogs.tea_cog.tea_cog import TeaCog
from cogs.view import ComfySDView, ComfySDXLView, UpscaleView
from cogs.civitai_cog.civitai_cog import CivitaiCog

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.default()
intents.message_content = True

if __name__ == "__main__":
    init_db()
    set_comfy_settings(get_system_info())

    from cogs.comfy_cog.comfy_cog import ComfyCog

    bot = discord.Bot(intents=intents)

    bot.loop.create_task(wsrun())

    @bot.event
    async def on_ready():
        bot.add_view(ComfySDView())
        bot.add_view(ComfySDXLView())
        bot.add_view(UpscaleView())

    bot.add_cog(ComfyCog())
    bot.add_cog(CivitaiCog())
    bot.add_cog(TeaCog(bot))
    bot.run(
        bot_token,
    )
