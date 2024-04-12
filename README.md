This bot is for personal use. You can use it as a guide for setting up your own bot based off of ComfyUI.

More features will be added over time for features I use a lot.

# TODO
- Add support for per model defaults. We need this to better support PonyDiffusion since it has its own way to handle prompts and negative prompts. Its also just better to handle defaults this way overall since different models have different reccomended defaults for them to work properly.
- Add support for some missing stable diffusion options.
- Fix that awful code duplication in actions/dream.py. It was thrown together to get the LLM to support image generation using the code already made for it. The progress and final result message handling needs to be redone to allow that duplication to be removed.


# Low Priority TODO
- Move the COG code to separate folders to make them more independent on one another. We will need a solution for COG to COG communication however since the TeaCog will use actions defined by the ComfyCog.
- Fix loras being directly baked into the system prompt. We can have a DB of loras and what to use with them that is sent with the system prompt instead.
- Investigate methods of trimming the system prompt since image generation takes up a lot of tokens on its own. We want to keep costs down but it gets complicated when we want to explain to chat GPT how to use the image generator including loras and character designs.
  - Maybe do a 2 step approach where we use an LLM to classify a message as being either for chat or for image generation and then use a tailored system prompt and context for it. This would mean 2 LLM calls per message but it should be overall cheaper.
  - There might be cheaper solutions if we want an LLM to generate an image prompt but I am not sure how cheap we can get it if we want the LLM to also support adding LORAs or character designs to a prompt. If we ditch LORAs then there are emerging solutions for this coming this year.
- Add support for other LLM APIs. Right now its only talking to OpenAI. This is mainly due to me having a 8GB VRAM limit so trying to run image generation and LLM suitable to chat with on the same computer wouldn't work well and will be slow.