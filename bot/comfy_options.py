from discord import option
import functools
from settings import size_range, default_steps, default_cfg, upscale_latent
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


def draw_options(default_negs, default_model, models, default_width, default_height, loras, default_hires):
    def inner(func):
        @option(
            'prompt',
            str,
            description='Prompt to draw with',
            required=True,
            )
        @option(
            'negative_prompt',
            str,
            description='Negative prompts to draw with',
            required=False,
            default=default_negs
        )
        @option(
            'model',
            str,
            description='Model to use for drawing',
            required=False,
            choices=models,
            default=default_model
        )
        @option(
            'width',
            int,
            description='Width of the image',
            required=False,
            choices=size_range,
            default=default_width
        )
        @option(
            'height',
            int,
            description='Height of the image',
            required=False,
            choices=size_range,
            default=default_height
        )
        @option(
            'steps',
            int,
            description='Steps to take to generate the image',
            min_value=1,
            max_value=100,
            required=False,
            default=default_steps
        )
        @option(
            'cfg',
            int,
            description='Classifier Free Guidance scale',
            min_value=1,
            max_value=13,
            required=False,
            default=default_cfg
        )
        @option(
            'seed',
            int,
            description='Seed to use. If not set a random one will be used.',
            min_value=1,
            max_value=4294967294,
            required=False,
        )
        @discord.option(
            'lora',
            str,
            description='LoRA to use',
            required=False,
            autocomplete=default_filter(loras)
        )
        @discord.option(
            'lora_two',
            str,
            description='Second LoRA to use',
            required=False,
            autocomplete=default_filter(loras)
        )
        @discord.option(
            'lora_three',
            str,
            description='Thrid LoRA to use',
            required=False,
            autocomplete=default_filter(loras)
        )
        @option(
            'hires',
            str,
            description='Enable hires fix. Width and Height will be the final resolution',
            required=False,
            choices=upscale_latent,
            default=default_hires
        )
        @option(
            'hires_strength',
            float,
            description='How strong the denoise is when doing hires fix',
            required=False,
            min_value=0,
            max_value=1,
            default=0.65
        )
        @option(
            'glitch',
            bool,
            description='Use the wrong VAE on purpose to create a glitchy mess',
            required=False,
            default=False
        )
        @functools.wraps(func)  # Not required, but generally considered good practice
        async def newfunc(*args, **kwargs):
            return await func(*args, **kwargs)
        return newfunc
    return inner
