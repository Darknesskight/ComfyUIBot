from enum import Enum
import random
from api.model_db import get_model_default, get_sd_default
import json

class SDType(Enum):
    SD = 'sd'
    SDXL = 'sdxl'

class SDOptions:

    prompt_template: str

    def __init__(
            self,
            sd_type: SDType,
            prompt: str,
            negative_prompt: str,
            model: str,
            width: int,
            height: int,
            steps: int,
            seed: int,
            cfg: float,
            sampler: str,
            scheduler: str,
            lora: str,
            lora_two: str,
            lora_three: str,
            hires: bool,
            hires_strength: float,
            prompt_template: str = None
    ):
        super().__init__()
        self.sd_type = sd_type
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.model = model
        self.width = width
        self.height = height
        self.steps = steps
        self.seed = seed or random.randint(1, 4294967294)
        self.cfg = cfg
        self.sampler = sampler
        self.scheduler = scheduler
        self.lora = lora
        self.lora_two = lora_two
        self.lora_three = lora_three
        self.hires = hires
        self.hires_strength = hires_strength
        self.prompt_template = prompt_template

    def to_json(self):
        # Manually handle the serialization of the enum
        data = self.__dict__.copy()
        data['sd_type'] = self.sd_type.value  # Convert enum to its value for JSON
        return json.dumps(data, sort_keys=True, indent=4)

    @classmethod
    def from_json(cls, json_str):
        json_dict = json.loads(json_str)
        # Manually handle the deserialization of the enum
        json_dict['sd_type'] = SDType(json_dict['sd_type'])  # Convert value back to enum
        return cls(**json_dict)

    @classmethod
    async def create(cls, **kwargs) -> 'SDOptions':
        self = cls(**kwargs)
        await self.set_defaults()
        self.merge_loras_into_prompt()
        self.apply_prompt_template()
        return self

    async def set_defaults(self):
        print(self.model)
        sd_default = await get_sd_default(self.sd_type.value)
        model_default = await get_model_default(self.model or sd_default.get("model"))
        print(sd_default)
        print(model_default)
        for param in self.__dict__:
            if getattr(self, param) is None:
                if model_default.get(param) is None:    
                    setattr(self, param, sd_default.get(param))
                else:
                    setattr(self, param, model_default.get(param))

    def merge_loras_into_prompt(self):
        loras = [self.lora, self.lora_two, self.lora_three]
        for lora in loras:
            if lora and lora != "None":
                self.prompt = f'{self.prompt} lora:{lora}:0.85'
    
    def apply_prompt_template(self):
        if self.prompt_template:
            if "<prompt>" in self.prompt_template:
                self.prompt = self.prompt_template.replace("<prompt>", self.prompt)
            else:
                self.prompt = self.prompt_template + " " + self.prompt
