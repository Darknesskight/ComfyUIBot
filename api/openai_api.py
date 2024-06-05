from openai import AsyncOpenAI
from api.chat_history_db import (
    get_server_prompt,
    get_user_prompt,
    get_chat_history,
    insert_chat_history,
    delete_single_chat,
)
import tiktoken
from settings import openai_api_key, openai_model, openai_truncate_limit

client = AsyncOpenAI(api_key=openai_api_key)


async def get_system_prompt():
    with open("system_prompt.txt", "r") as file:
        return (file.read()).strip()


async def truncate_history(server_id, max_tokens):
    # Get the full chat history for the server
    chat_history = await get_chat_history(server_id)
    messages = [message for message, _ in chat_history]

    # Convert the chat history into a single string to count tokens
    history_str = " ".join(messages)
    encoding = tiktoken.encoding_for_model(openai_model)
    tokens = len(encoding.encode(history_str))

    # If the token limit is exceeded, remove the oldest messages
    while tokens > max_tokens and chat_history:
        # Remove the oldest entry (first in the list)
        oldest_message = chat_history.pop(0)
        print(oldest_message)
        await delete_single_chat(server_id, oldest_message[0], oldest_message[1])

        # Recalculate the token count
        history_str = " ".join([message for message, _ in chat_history])
        tokens = len(encoding.encode(history_str))


# Example of sending a message and updating chat history in the database
async def send_message(server_id, user_id, username, prompt, b64_image):
    system_prompt = await get_system_prompt()
    server_prompt = await get_server_prompt(server_id)
    user_prompt = await get_user_prompt(user_id)
    if server_prompt:
        system_prompt = system_prompt + "\n" + server_prompt
    if user_prompt:
        system_prompt = (
            system_prompt
            + "\n"
            + f"Here are items {username} wants you to remember\n{user_prompt}\nWhen interacting with {username} keep those items in mind."
        )
    print(server_prompt + "\n" + user_prompt)
    chat_history = await get_chat_history(server_id)
    messages = [{"role": role, "content": message} for message, role in chat_history]
    if b64_image:
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                    },
                ],
            }
        )
    else:
        messages.append({"role": "user", "content": prompt})
    response = await client.chat.completions.create(
        model=openai_model,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        max_tokens=4096,
    )
    assistant_message = response.choices[0].message.content
    print(response.choices[0])
    await insert_chat_history(server_id, prompt, "user")
    await insert_chat_history(server_id, assistant_message, "assistant")
    await truncate_history(server_id, openai_truncate_limit)
    return assistant_message
