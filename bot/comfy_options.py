from discord import option
import functools
from settings import size_range, default_steps, default_cfg

def draw_options(default_negs, default_model, models, default_width, default_height):
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
