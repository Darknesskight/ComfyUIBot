from discord.ext import commands
import discord
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Autocomplete function (must be defined before the class)
async def get_loaded_cogs(ctx: discord.AutocompleteContext):
    """Autocomplete function for cog names"""
    bot = ctx.bot
    return [ext_name for ext_name in bot.extensions.keys()]

class AdminCog(commands.Cog, name="Admin", description="Admin commands for managing cogs and bot operations"):
    def __init__(self, bot):
        self.bot = bot

    admin = discord.SlashCommandGroup(name="admin", description="Admin commands")

    @admin.command(name="list_cogs", description="List all loaded cogs")
    @commands.is_owner()
    async def list_cogs(self, ctx: discord.ApplicationContext):
        """List all currently loaded cogs"""
        await ctx.response.defer()
        
        embed = discord.Embed(
            title="Loaded Cogs",
            description=f"Total cogs: {len(self.bot.cogs)}",
            color=discord.Color.blue()
        )
        
        for cog_name, cog in self.bot.cogs.items():
            embed.add_field(
                name=cog_name,
                value=f"Description: {cog.description or 'No description'}",
                inline=False
            )
        
        await ctx.followup.send(embed=embed)

    @admin.command(name="load_cog", description="Load a new cog")
    @commands.is_owner()
    @discord.option(
        "cog_path",
        description="Path to the cog (e.g., cogs.comfy_cog.comfy_cog)",
        type=str,
        required=True
    )
    async def load_cog(self, ctx: discord.ApplicationContext, cog_path: str):
        """Load a new cog into the bot"""
        await ctx.response.defer()
        
        try:
            # Check if cog is already loaded
            cog_name = cog_path.split('.')[-1]
            if cog_name in self.bot.cogs:
                await ctx.followup.send(f"Cog `{cog_name}` is already loaded!", ephemeral=True)
                return
            
            # Try to load the cog
            await self.bot.load_extension(cog_path)
            logger.info(f"Successfully loaded cog: {cog_path}")
            await ctx.followup.send(f"✅ Successfully loaded cog: `{cog_path}`")
            
        except Exception as e:
            logger.error(f"Failed to load cog {cog_path}: {e}")
            await ctx.followup.send(f"❌ Failed to load cog `{cog_path}`: {str(e)}", ephemeral=True)
            raise

    @admin.command(name="unload_cog", description="Unload a cog")
    @commands.is_owner()
    @discord.option(
        "cog_name",
        description="Name of the cog to unload",
        type=str,
        required=True,
        autocomplete=get_loaded_cogs
    )
    async def unload_cog(self, ctx: discord.ApplicationContext, cog_name: str):
        """Unload a cog from the bot"""
        await ctx.response.defer()
        
        try:
            if cog_name not in self.bot.cogs:
                await ctx.followup.send(f"Cog `{cog_name}` is not loaded!", ephemeral=True)
                return
            
            # Don't allow unloading the admin cog itself
            if cog_name == "Admin":
                await ctx.followup.send("❌ Cannot unload the Admin cog!", ephemeral=True)
                return
            
            # Find the extension path by checking all extensions
            extension_path = None
            for ext_name in self.bot.extensions.keys():
                # Check if the extension contains the cog class
                try:
                    ext_module = self.bot.extensions[ext_name]
                    if hasattr(ext_module, cog_name):
                        extension_path = ext_name
                        break
                except:
                    continue
            
            if not extension_path:
                # Try to construct the path from common patterns
                extension_path = f"cogs.{cog_name.lower()}_cog.{cog_name.lower()}_cog"
            
            self.bot.unload_extension(extension_path)
            logger.info(f"Successfully unloaded cog: {cog_name}")
            await ctx.followup.send(f"✅ Successfully unloaded cog: `{cog_name}`")
            
        except Exception as e:
            logger.error(f"Failed to unload cog {cog_name}: {e}")
            await ctx.followup.send(f"❌ Failed to unload cog `{cog_name}`: {str(e)}", ephemeral=True)

    @admin.command(name="reload_cog", description="Reload a cog")
    @commands.is_owner()
    @discord.option(
        "extension",
        description="Name of the cog to reload",
        type=str,
        required=True,
        autocomplete=get_loaded_cogs
    )
    async def reload_cog(self, ctx: discord.ApplicationContext, extension: str):
        """Reload a cog"""
        await ctx.response.defer()
        
        try:
            # Check if cog exists
            if extension not in self.bot.extensions:
                await ctx.followup.send(f"Cog `{extension}` is not loaded!", ephemeral=True)
                return
            
            # Reload the extension
            self.bot.reload_extension(extension)
            logger.info(f"Successfully reloaded cog: {extension}")
            await ctx.followup.send(f"✅ Successfully reloaded cog: `{extension}`")
            
        except Exception as e:
            logger.error(f"Failed to reload cog {extension}: {e}")
            await ctx.followup.send(f"❌ Failed to reload cog `{extension}`: {str(e)}", ephemeral=True)

    @admin.command(name="bot_status", description="Get bot status information")
    @commands.is_owner()
    async def bot_status(self, ctx: discord.ApplicationContext):
        """Get detailed bot status information"""
        await ctx.response.defer()
        
        # Calculate total users across all guilds
        total_users = 0
        for guild in self.bot.guilds:
            total_users += guild.member_count or 0
        
        embed = discord.Embed(
            title="Bot Status",
            description=f"Bot: {self.bot.user}",
            color=discord.Color.green()
        )
        
        # Basic info
        embed.add_field(name="Guilds", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Users", value=total_users, inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        
        # Cog info
        embed.add_field(name="Loaded Cogs", value=len(self.bot.cogs), inline=True)
        embed.add_field(name="Extensions", value=len(self.bot.extensions), inline=True)
        
        # Websocket status
        websocket_status = "🟢 Connected" if hasattr(self.bot, 'websocket_started') and self.bot.websocket_started else "🔴 Disconnected"
        embed.add_field(name="Websocket", value=websocket_status, inline=True)
        
        await ctx.followup.send(embed=embed)

    @admin.command(name="restart_websocket", description="Restart the websocket connection")
    @commands.is_owner()
    async def restart_websocket(self, ctx: discord.ApplicationContext):
        """Restart the websocket connection to ComfyUI"""
        await ctx.response.defer()
        
        try:
            from api.websocket_subsystem import stop_websocket, start_websocket
            
            # Stop existing websocket
            if hasattr(self.bot, 'websocket_started') and self.bot.websocket_started:
                stop_websocket()
                self.bot.websocket_started = False
            
            # Start new websocket
            start_websocket(self.bot.loop)
            self.bot.websocket_started = True
            
            logger.info("Websocket connection restarted")
            await ctx.followup.send("✅ Websocket connection restarted successfully")
            
        except Exception as e:
            logger.error(f"Failed to restart websocket: {e}")
            await ctx.followup.send(f"❌ Failed to restart websocket: {str(e)}", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("AdminCog is ready")

def setup(bot):
    bot.add_cog(AdminCog(bot))
