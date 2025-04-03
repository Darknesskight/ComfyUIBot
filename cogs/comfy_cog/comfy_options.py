from discord import option
import functools
from settings import size_range, upscale_latent, samplers, schedulers
import discord


def default_filter(list):
    async def searcher(ctx: discord.AutocompleteContext):
        string_starts_with = []
        anywhere_in_string = []
        for item in list:
            if item.name.lower().startswith(str(ctx.value or "").lower()):
                string_starts_with.append(item)
            elif str(ctx.value or "").lower() in item.name.lower():
                anywhere_in_string.append(item)
        final_list = string_starts_with + anywhere_in_string
        if not final_list:
            final_list.append("None")
        return final_list

    return searcher


def draw_options(
    models,
    loras,
):
    def inner(func):
        @option(
            "prompt",
            str,
            description="Prompt to draw with",
            required=True,
        )
        @option(
            "negative_prompt",
            str,
            description="Negative prompts to draw with",
            required=False
        )
        @option(
            "model",
            str,
            description="Model to use for drawing",
            required=False,
            choices=models
        )
        @option(
            "width",
            int,
            description="Width of the image",
            required=False,
            choices=size_range
        )
        @option(
            "height",
            int,
            description="Height of the image",
            required=False,
            choices=size_range
        )
        @option(
            "steps",
            int,
            description="Steps to take to generate the image",
            min_value=1,
            max_value=100,
            required=False
        )
        @option(
            "cfg",
            int,
            description="Classifier Free Guidance scale",
            min_value=1,
            max_value=13,
            required=False
        )
        @option(
            "sampler",
            str,
            description="Sampler to use for the drawing",
            required=False,
            autocomplete=default_filter(samplers),
        )
        @option(
            "scheduler",
            str,
            description="Scheduler to use for the drawing",
            required=False,
            autocomplete=default_filter(schedulers),
        )
        @option(
            "seed",
            int,
            description="Seed to use. If not set a random one will be used.",
            min_value=1,
            max_value=4294967294,
            required=False,
        )
        @option(
            "lora",
            str,
            description="LoRA to use",
            required=False,
            autocomplete=default_filter(loras),
        )
        @option(
            "lora_two",
            str,
            description="Second LoRA to use",
            required=False,
            autocomplete=default_filter(loras),
        )
        @option(
            "lora_three",
            str,
            description="Thrid LoRA to use",
            required=False,
            autocomplete=default_filter(loras),
        )
        @option(
            "hires",
            str,
            description="Enable hires fix. Width and Height will be the final resolution",
            required=False,
            choices=upscale_latent
        )
        @option(
            "hires_strength",
            float,
            description="How strong the denoise is when doing hires fix",
            required=False,
            min_value=0,
            max_value=1
        )
        @functools.wraps(func)  # Not required, but generally considered good practice
        async def newfunc(*args, **kwargs):
            return await func(*args, **kwargs)

        return newfunc

    return inner




def default_options(models):
    def inner(func):
        @option(
            "model",
            str,
            description="Model to use for drawing",
            required=True,
            autocomplete=default_filter(models),
        )
        @option(
            "prompt_template",
            str,
            required=False,
            description="Set a template to map prompts to. Use <prompt> for where the user's prompt goes.",
        )
        @option(
            "negative_prompt",
            str,
            required=False,
            description="Set the default negative prompt to use",
        )
        @option(
            "width",
            int,
            description="Default width",
            required=False,
            choices=size_range,
        )
        @option(
            "height",
            int,
            description="Default height",
            required=False,
            choices=size_range,
        )
        @option(
            "steps",
            int,
            description="Default steps to take to generate the image",
            min_value=1,
            max_value=100,
            required=False,
        )
        @option(
            "cfg",
            float,
            description="Default Classifier Free Guidance scale",
            min_value=1,
            max_value=13,
            required=False,
        )
        @option(
            "sampler",
            str,
            description="Sampler to use for the drawing",
            required=False,
            autocomplete=default_filter(samplers),
        )
        @option(
            "scheduler",
            str,
            description="Scheduler to use for the drawing",
            required=False,
            autocomplete=default_filter(schedulers),
        )
        @option(
            "hires",
            str,
            description="Default hires setting",
            required=False,
            choices=upscale_latent,
        )
        @option(
            "hires_strength",
            float,
            description="Default strength for hires",
            required=False,
            min_value=0,
            max_value=1,
        )
        @functools.wraps(func)  # Not required, but generally considered good practice
        async def newfunc(*args, **kwargs):
            return await func(*args, **kwargs)

        return newfunc

    return inner