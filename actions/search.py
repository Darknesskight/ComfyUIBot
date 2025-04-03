from typing import Any, Coroutine
import discord
from api.civitai_api import search_models
from io import StringIO
from html.parser import HTMLParser
from discord.ext.pages import Paginator, Page
from discord import SelectOption
import traceback
import json


async def search(
    ctx: discord.ApplicationContext,
    type,
    query,
    base_model,
    sort,
    period,
):
    await ctx.response.defer()
    try:
        results = await search_models(type, query, base_model, sort, period)
        items = process_results(results["items"])

        if not items:
            await ctx.followup.send(
                "Civitai returned no results. Please adjust the query and try again."
            )
            return

        pages = []
        for item in items:
            pages.append(CivitaiPage(embeds=[create_search_embed(item)], item=item))

        paginator = CivitaiPaginator(pages=pages)

        await paginator.respond(interaction=ctx.interaction)
    except Exception as e:
        print(e)
        traceback.print_exc()
        await ctx.followup.send("Unable to search Civitai. Please see log for details")


def create_search_embed(item, model_version_index=0):
    embed = discord.Embed(
        title=item["name"],
        description=f"URL: https://civitai.com/models/{item['id']}",
        color=discord.Colour.blue(),
    )
    s = MLStripper()

    model_version = item["modelVersions"][model_version_index]
    images = model_version["images"]
    creator = item.get("creator", None)
    stats = item["stats"]

    version = model_version["name"]
    model_type = item["type"]
    base_model = model_version["baseModel"]

    downloads = stats["downloadCount"]
    favorites = stats["favoriteCount"]
    rating = f"{stats['rating']} ({stats['ratingCount']})"

    tags = ", ".join(item["tags"])
    trigger_words = "\n".join(model_version["trainedWords"])

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
    if trigger_words:
        embed.add_field(name="Trigger Words", value=trigger_words, inline=False)
    embed.set_image(url=image or None)
    if creator:
        embed.set_author(
            name=creator["username"], icon_url=creator["image"] or discord.Embed.Empty
        )
    embed.set_footer(text=f"1/{len(images)}")

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


# This is mostly to allow for taking out the non images from the image list.
def process_results(items):
    for item in items:
        for model_version in item["modelVersions"]:
            model_version["images"] = filter_images(model_version["images"])
    return items


def filter_images(images):
    if not images and type(images) != list:
        return []

    filtered_images = []
    for image in images:
        print(image)
        if image["type"] == "image":
            filtered_images.append(image)

    return filtered_images


class CivitaiPage(Page):
    current_image = 0
    current_model_version = 0
    max_images = 0

    def __init__(self, embeds, item):
        super().__init__(embeds=embeds)
        self.item = item
        self.max_images = len(item["modelVersions"][0]["images"])


class CivitaiPaginator(Paginator):
    paginator: Paginator = None

    def __init__(self, pages: list[CivitaiPage]):
        super().__init__(pages=pages, author_check=False)
        self.custom_view = CivitaiView(self)

    async def next_image(self, interaction):
        page = self.get_current_page()
        embed = page.embeds[0]

        images = page.item["modelVersions"][page.current_model_version]["images"]
        if page.max_images > page.current_image + 1:
            embed.set_image(url=images[page.current_image + 1]["url"])
            embed.set_footer(text=f"{page.current_image + 2}/{len(images)}")
            page.current_image = page.current_image + 1

            self.custom_view = CivitaiView(self)
            await self.goto_page(self.current_page, interaction=interaction)

    async def prev_image(self, interaction):
        page = self.get_current_page()
        embed = page.embeds[0]

        images = self.get_current_page().item["modelVersions"][
            page.current_model_version
        ]["images"]
        if page.current_image > 0:
            embed.set_image(url=images[page.current_image - 1]["url"])
            embed.set_footer(text=f"{page.current_image}/{len(images)}")
            page.current_image = page.current_image - 1

            self.custom_view = CivitaiView(self)
            await self.goto_page(self.current_page, interaction=interaction)

    async def switch_version(self, model_version_index, interaction):
        page = self.get_current_page()

        embed = create_search_embed(page.item, model_version_index)
        page.embeds = [embed]
        page.current_image = 0
        page.current_model_version = model_version_index

        self.custom_view = CivitaiView(self)
        await self.goto_page(self.current_page, interaction=interaction)

    def get_current_page(self) -> CivitaiPage:
        return self.pages[self.current_page]

    async def goto_page(self, page_number, *args, **kwargs):
        self.current_page = page_number
        self.custom_view = CivitaiView(self)
        return await super().goto_page(page_number, *args, **kwargs)


class CivitaiView(discord.ui.View):
    def __init__(self, paginator: CivitaiPaginator):
        super().__init__()
        self.paginator = paginator

        page = self.paginator.get_current_page()

        # Don't bother showing the select if we have only 1 version.
        if len(page.item["modelVersions"]) > 1:
            self.add_item(SwitchVersionSelect(self, "civitai_model_version_select"))

        self.add_item(
            PreviousImageButton(self, "civitai_image_prev", page.current_image <= 0)
        )
        self.add_item(
            NextImageButton(
                self, "civitai_image_next", page.current_image + 1 >= page.max_images
            )
        )


class NextImageButton(discord.ui.Button):
    def __init__(self, parent_view: CivitaiView, custom_id, disabled):
        super().__init__(custom_id=custom_id, label="Next Image", disabled=disabled)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.paginator.next_image(interaction)


class PreviousImageButton(discord.ui.Button):
    def __init__(self, parent_view: CivitaiView, custom_id, disabled):
        super().__init__(custom_id=custom_id, label="Previous Image", disabled=disabled)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.paginator.prev_image(interaction)


# Select dropdown for models.
class SwitchVersionSelect(discord.ui.Select):
    def __init__(self, parent_view: CivitaiView, custom_id):
        self.parent_view = parent_view
        page = self.parent_view.paginator.get_current_page()
        options = []
        for index, model_version in enumerate(page.item["modelVersions"]):
            options.append(SelectOption(label=model_version["name"], value=str(index)))

        super().__init__(
            placeholder="Switch model version",
            custom_id=custom_id,
            options=options[:25],
        )

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.paginator.switch_version(
            int(self.values[0]), interaction
        )
