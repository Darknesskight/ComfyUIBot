from discord.ext import commands
from discord import Message, Bot, ApplicationContext, slash_command
from api.tea_db import init_tea_db, toggle_guild_autoreply, toggle_user_optout
from api.chat_history_db import (
    init_chat_db,
    clear_chat_history,
    update_server_prompt,
    update_user_prompt,
    get_server_prompt,
    get_user_prompt,
)
from bot.tea_cog_message_queue import TeaCogMessageQueue
from bot.view import ServerPromptModal, UserPromptModal


MAX_LENGTH = 1500


class TeaCog(commands.Cog, name="OpenAI", description="Respond to users"):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.message_queue = TeaCogMessageQueue(bot)

    @slash_command(
        name="autoreply",
        description="Enable Tea autoreply for this channel. Rerun in the same channel to disable",
    )
    async def autoreply(self, ctx: commands.Context):
        await ctx.response.defer()
        guild_autoreplying = await toggle_guild_autoreply(ctx.guild.id, ctx.channel.id)

        if guild_autoreplying:
            await ctx.followup.send(
                f"Tea will now autoreply in this channel. Rerun to disable."
            )
        else:
            await ctx.followup.send(
                f"Tea will no longer autoreply in this channel. Rerun to enable."
            )

    @slash_command(
        name="optout", description="Opt out of Tea processesing your messages."
    )
    async def optout(self, ctx: commands.Context):
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
    @commands.has_guild_permissions(manage_messages=True)
    async def clear_history(self, ctx: ApplicationContext):
        await ctx.response.defer(invisible=False)
        await clear_chat_history(ctx.guild.id)
        await ctx.followup.send("Tea's history has been cleared.")

    @slash_command(name="serverprompt", description="Add/Update a custom server prompt")
    @commands.has_guild_permissions(manage_messages=True)
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
            or message.content.startswith("!")
        ):
            return

        await self.message_queue.queue_message(message)
