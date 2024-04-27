from discord.ext import commands
import discord
from actions.search import search
from .civitai_options import civitai_options


class CivitaiCog(
    commands.Cog, name="Civitai", description="Search civitai for models/loras"
):
    @discord.command(
        name="civitai", description="Search for models or LoRAs on Civitai"
    )
    @civitai_options()
    async def dream_sd(
        self,
        ctx: discord.ApplicationContext,
        type,
        query,
        base_model,
        sort,
        period,
    ):
        await search(
            ctx, type=type, query=query, base_model=base_model, sort=sort, period=period
        )
