import json
import aiohttp
import urllib.parse
from settings import server_ip, client_id


def get_address():
    return "http://{}".format(server_ip)


async def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode("utf-8")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{get_address()}/prompt", data=data, headers={'Content-Type': 'application/json'}) as response:
            response.raise_for_status()
            return await response.json()


async def get_system_info():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{get_address()}/object_info") as response:
            response.raise_for_status()
            return await response.json()


async def get_history(prompt_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{get_address()}/history/{prompt_id}") as response:
            response.raise_for_status()
            return await response.json()


async def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{get_address()}/view?{url_values}") as response:
            response.raise_for_status()
            return await response.read()
