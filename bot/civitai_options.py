from discord import option
import functools


def civitai_options():
    def inner(func):
        @option(
            "type",
            str,
            description="Search for checkpoint (model) or LoRA",
            required=False,
            choices=["Checkpoint", "LORA"],
        )
        @option(
            "base_model",
            str,
            description="Base model to use in search",
            required=False,
            choices=["SD 1.5", "SDXL 1.0"],
        )
        @option("query", str, description="Query to use in search", required=False)
        @option(
            "sort",
            str,
            description="Sort order (default: Highest Rated)",
            required=False,
            choices=["Highest Rated", "Most Downloaded", "Newest"],
            default="Highest Rated",
        )
        @option(
            "period",
            str,
            description="Peroid to limit query to (default: Month)",
            required=False,
            choices=["AllTime", "Year", "Month", "Week", "Day"],
            default="Month",
        )
        @functools.wraps(func)  # Not required, but generally considered good practice
        async def newfunc(*args, **kwargs):
            return await func(*args, **kwargs)

        return newfunc

    return inner
