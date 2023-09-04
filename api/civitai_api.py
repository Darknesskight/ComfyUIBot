import json
import aiohttp


def get_address():
    return "https://civitai.com/api/v1"


async def search_models(type, query, base_model, sort, period):
    params = {
        "types": type,
        "query": query,
        "baseModels": base_model,
        "limit": 10,
        "nsfw": "false",
        "sort": sort,
        "period": period,
    }
    params = {k: v for k, v in params.items() if v}
    print(params)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{get_address()}/models", params=params) as resp:
            return await resp.json()
