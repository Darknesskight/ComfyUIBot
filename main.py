from settings import bot_token, set_comfy_settings, server_ip, client_id
import threading
from comfy_cog import ComfyCog, ComfySDView, ComfySDXLView
from comfy_api import get_system_info
from comfy_websocket import wsrun
from job_db import init_db
import discord
import websockets
import asyncio


uri=f"ws://{server_ip}/ws?clientId={client_id}"



 # Starts receive things, not only once


# if __name__ == "__main__":
#     open_connection()
#     init_db()
#     set_comfy_settings(get_system_info())

#     asyncio.create_task(test())

#     bot = discord.Bot()

#     @bot.event
#     async def on_ready():
#         bot.add_view(ComfySDView())
#         bot.add_view(ComfySDXLView())

#     bot.add_cog(ComfyCog())
#     bot.run(bot_token)

if __name__ == "__main__":
    init_db()
    set_comfy_settings(get_system_info())

    bot = discord.Bot()

    asyncio.get_event_loop().create_task(wsrun())

    @bot.event
    async def on_ready():
        bot.add_view(ComfySDView())
        bot.add_view(ComfySDXLView())

    bot.add_cog(ComfyCog())
    bot.run(bot_token, )