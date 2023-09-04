import discord
from api.civitai_api import search_models
from io import StringIO
from html.parser import HTMLParser
from discord.ext.pages import Paginator, Page
import traceback


async def search(
    ctx: discord.ApplicationContext | discord.Interaction,
    type,
    query,
    base_model,
    sort,
    period,
):
    await ctx.response.defer()
    try:
        results = await search_models(type, query, base_model, sort, period)
        items = results["items"]

        if not items:
            await ctx.followup.send(
                "Civitai returned no results. Please adjust the query and try again."
            )
            return

        pages = []
        for item in items:
            pages.append(Page(embeds=[create_search_embed(item)]))

        paginator = Paginator(pages=pages, author_check=False)
        await paginator.respond(ctx.interaction)
    except Exception as e:
        print(e)
        traceback.print_exc()
        await ctx.followup.send("Unable to search Civitai. Please see log for details")


def create_search_embed(item):
    embed = discord.Embed(
        title=item["name"],
        description=f"URL: https://civitai.com/models/{item['id']}",
        color=discord.Colour.blue(),
    )
    s = MLStripper()

    model_version = item["modelVersions"][0]
    images = model_version["images"]
    creator = item["creator"]
    stats = item["stats"]

    version = model_version["name"]
    model_type = item["type"]
    base_model = model_version["baseModel"]

    downloads = stats["downloadCount"]
    favorites = stats["favoriteCount"]
    rating = f"{stats['rating']} ({stats['ratingCount']})"

    tags = ", ".join(item["tags"])

    s.feed(item["description"])
    description = s.get_data()
    description = (description[:200] + "..") if len(description) > 75 else description

    image = images[0]["url"] if len(images) > 0 else None

    embed.add_field(name="Version", value=version)
    embed.add_field(name="Type", value=model_type)
    embed.add_field(name="Base Model", value=base_model)

    embed.add_field(name="Downloads", value=downloads)
    embed.add_field(name="Favorites", value=favorites)
    embed.add_field(name="Ratings", value=rating)

    embed.add_field(name="Description", value=description, inline=False)
    embed.add_field(name="Tags", value=tags, inline=False)
    embed.set_image(url=image or discord.Embed.Empty)
    embed.set_author(
        name=creator["username"], icon_url=creator["image"] or discord.Embed.Empty
    )

    return embed


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()
