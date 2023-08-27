from settings import bot_token, set_comfy_settings
from api.comfy_api import get_system_info
from api.comfy_websocket import wsrun
from api.job_db import init_db
import discord
import asyncio


if __name__ == "__main__":
    init_db()
    set_comfy_settings(get_system_info())

    from bot.comfy_cog import ComfyCog, ComfySDView, ComfySDXLView

    bot = discord.Bot()

    asyncio.get_event_loop().create_task(wsrun())

    @bot.event
    async def on_ready():
        bot.add_view(ComfySDView())
        bot.add_view(ComfySDXLView())

    bot.add_cog(ComfyCog())
    bot.run(bot_token, )