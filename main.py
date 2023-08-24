import os
import uuid
from comfy_api import ComfyApi, ComfyWebsocket
from settings import Settings
import discord
import sqlite3
from job_db import JobDB
from dotenv import load_dotenv

load_dotenv()

server_ip = os.getenv("COMFY_IP")
client_id = str(uuid.uuid4())

comfy_api = ComfyApi(server_ip, client_id)
comfy_websocket = ComfyWebsocket(server_ip, client_id)
job_db = JobDB()

settings = Settings(comfy_api)
conn = sqlite3.connect("job.db")

comfy_websocket.start()
settings.load_settings()

# Delayed loading so that it gets the latest settings from Comfy to use in
# the select decorators.
# TODO: Look into a better way to do this.
from comfy_cog import ComfyCog, ComfySDView, ComfySDXLView

bot = discord.Bot()

@bot.event
async def on_ready():
    bot.add_view(ComfySDView(comfy_api, comfy_websocket, job_db))
    bot.add_view(ComfySDXLView(comfy_api, comfy_websocket, job_db))

bot.add_cog(ComfyCog(bot, settings, comfy_api, comfy_websocket, job_db))
bot.run(os.getenv("BOT_TOKEN"))
