import json
import aiohttp
import traceback


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
            try:
                return await resp.json()
            except Exception as e:
                print(e)
                print(resp.status)
                traceback.print_exc()
                raise e
