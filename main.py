import discord
import asyncio

from settings import bot_token, set_comfy_settings
from api.comfy_api import get_system_info
from api.websocket_subsystem import start_websocket, stop_websocket
from api.job_db import init_db
from cogs.view import ComfySDView, ComfySDXLView, UpscaleView, FluxView
from utils.logging_config import setup_logging, get_logger

# Configure logging
setup_logging()
logger = get_logger(__name__)

intents = discord.Intents.default()
intents.message_content = True

class ComfyUIBot(discord.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.websocket_started = False

    async def setup_hook(self):
        """Called before the bot starts. Perfect for initialization tasks."""
        logger.info("Setting up bot...")
        
        # Initialize database
        init_db()

        # Add persistent views
        self.add_view(ComfySDView())
        self.add_view(ComfySDXLView())
        self.add_view(UpscaleView())
        self.add_view(FluxView())
        logger.info("Persistent views added")

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        try:
            logger.info("Fetching ComfyUI system info...")
            system_info = await get_system_info()
            logger.info(f"System info retrieved with keys: {list(system_info.keys())}")
            await set_comfy_settings(system_info)
            logger.info("ComfyUI settings loaded successfully")
            self._system_info_loaded = True
        except Exception as e:
            logger.error(f"Failed to load ComfyUI settings: {e}")
            logger.warning("Bot will continue without ComfyUI integration")
            self._system_info_loaded = True
        
        # Start websocket connection after bot is fully ready
        if not self.websocket_started:
            start_websocket(self.loop)
            self.websocket_started = True
            logger.info("Websocket subsystem started in on_ready")

    async def close(self):
        """Clean shutdown"""
        logger.info("Shutting down bot...")
        if self.websocket_started:
            stop_websocket()
        await super().close()

async def main():
    """Main async function to run the bot"""
    bot = ComfyUIBot(intents=intents)
    
    # Load cogs as extensions for proper reload functionality
    bot.load_extension("cogs.comfy_cog.comfy_cog")
    bot.load_extension("cogs.tea_cog.tea_cog")
    bot.load_extension("cogs.admin_cog.admin_cog")
    
    try:
        await bot.start(bot_token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        await bot.close()
    except Exception as e:
        logger.error(f"Bot encountered an error: {e}")
        await bot.close()
        raise

if __name__ == "__main__":
    # Run the bot with proper async handling
    asyncio.run(main())
