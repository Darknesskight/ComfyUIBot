from discord.ext import commands
from discord import Message, Bot, ApplicationContext, slash_command, option
import functools
from models.autoreply import GuildAutoReply
from api.tea_db import init_tea_db, toggle_guild_autoreply, toggle_user_optout
from api.chat_history_db import (
    init_chat_db,
    clear_chat_history,
    update_server_prompt,
    update_user_prompt,
    get_server_prompt,
    get_user_prompt,
)
from .tea_cog_message_queue import TeaCogMessageQueue
from cogs.view import ServerPromptModal, UserPromptModal


MAX_LENGTH = 1500


def is_owner_or_admin():
    def decorator(func):

        @functools.wraps(func)
        async def wrapper(self, ctx: ApplicationContext, *args, **kwargs):
            # Permission checks
            if await ctx.bot.is_owner(ctx.author):
                return await func(self, ctx, *args, **kwargs)
            if ctx.author == ctx.guild.owner:
                return await func(self, ctx, *args, **kwargs)
            if ctx.author.guild_permissions.administrator:
                return await func(self, ctx, *args, **kwargs)

            # If check fails
            await ctx.respond("You do not have the necessary permissions to run this command.")
        return wrapper
    return decorator


class TeaCog(commands.Cog, name="OpenAI", description="Respond to users"):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.message_queue = TeaCogMessageQueue(bot)

    @slash_command(
        name="autoreply",
        description="Enable Tea autoreply for this channel. Rerun in the same channel to disable",
    )
    @is_owner_or_admin()
    @option(
        "prefix",
        str,
        description="Prefix to use for messages to get ignored",
        max_length=1,
        default="!",
    )
    @option(
        "reverse_check",
        bool,
        description="Set to true to require prefix for message to be processed",
        default=False,
    )
    async def autoreply(self, ctx: ApplicationContext, prefix, reverse_check):
        await ctx.response.defer()

        guild_autoreply = GuildAutoReply(ctx.channel.id, prefix, reverse_check)

        guild_autoreplying = await toggle_guild_autoreply(ctx.guild.id, guild_autoreply)
        addon_message = f"Use the prefix `{guild_autoreply.prefix}` at the start of your message to have Tea {'see' if guild_autoreply.reverse_check else 'ignore'} your message."

        if guild_autoreplying:
            await ctx.followup.send(
                f"Tea will now autoreply in this channel. Rerun to disable. {addon_message}"
            )
        else:
            await ctx.followup.send(
                f"Tea will no longer autoreply in this channel. Rerun to enable."
            )

    @slash_command(
        name="optout", description="Opt out of Tea processesing your messages."
    )
    async def optout(self, ctx: ApplicationContext):
        await ctx.response.defer()
        user_opted_out = await toggle_user_optout(ctx.author.name)

        if user_opted_out:
            await ctx.followup.send(
                f"Tea will no longer see your messages. Rerun to undo."
            )
        else:
            await ctx.followup.send(
                f"Tea will now see your messages again. Rerun to disable."
            )

    @slash_command(name="cleartea", description="Clear Tea's history")
    @is_owner_or_admin()
    async def clear_history(self, ctx: ApplicationContext):
        await ctx.response.defer(invisible=False)
        await clear_chat_history(ctx.guild.id)
        await ctx.followup.send("Tea's history has been cleared.")

    @slash_command(name="serverprompt", description="Add/Update a custom server prompt")
    @is_owner_or_admin()
    async def server_prompt(self, ctx: ApplicationContext):
        async def on_modal_submit(prompt):
            await update_server_prompt(ctx.guild.id, prompt)

        server_prompt = await get_server_prompt(ctx.guild.id)
        modal = ServerPromptModal(server_prompt, on_modal_submit)
        await ctx.interaction.response.send_modal(modal)

    @slash_command(name="remember", description="Have Tea remember something about you")
    async def user_prompt(self, ctx: ApplicationContext):
        async def on_modal_submit(prompt):
            await update_user_prompt(ctx.author.id, prompt)

        user_prompt = await get_user_prompt(ctx.author.id)
        modal = UserPromptModal(user_prompt, on_modal_submit)
        await ctx.interaction.response.send_modal(modal)

    @commands.Cog.listener()
    async def on_ready(self):
        await init_tea_db()
        await init_chat_db()

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if (
            message.author.bot
            or not message.content.strip()
        ):
            return

        await self.message_queue.queue_message(message)
