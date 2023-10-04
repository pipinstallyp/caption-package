import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation import GenerationConfig

class QwenCap:
    model: AutoModelForCausalLM = None
    tokenizer: AutoTokenizer = None

    def __init__(self, device:str=None, model_name:str=None) -> None:
        self.model_name = model_name if model_name else "pipyp/qwenchatreup"
        self.device = device if device else "cuda"

        # If you expect the results to be reproducible, set a random seed.
        torch.manual_seed(1234)

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)

        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, device_map=self.device, trust_remote_code=True).eval()
        self.model.generation_config = GenerationConfig.from_pretrained(self.model_name, trust_remote_code=True)

    def chat(self, image_path:str, text:str) -> str:
        query = self.tokenizer.from_list_format([
            {'image': image_path},
            {'text': text},
        ])
        response, history = self.model.chat(self.tokenizer, query=query, history=None)
        return response
