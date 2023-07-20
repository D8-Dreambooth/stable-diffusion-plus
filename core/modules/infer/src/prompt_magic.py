import json
import re
import socket
import logging
from dataclasses import dataclass
from typing import List, Dict

import requests

logger = logging.getLogger(__name__)


class ChatParams:
    user_input: str = ''
    history: Dict[str, List[str]] = {'internal': [], 'visible': []}
    mode: str = 'chat'
    character: str = ''
    instruction_template: str = 'Wizard-Mega'
    regenerate: bool = False
    _continue: bool = False
    stop_at_newline: bool = False
    chat_prompt_size: int = 2048
    chat_generation_attempts: int = 1
    chat_instruct_command: str = 'Continue the chat dialogue below. Write a single reply for the character "".\n\n'
    max_new_tokens: int = 80
    temperature: float = 0.7
    top_k: int = 30
    top_p: float = 0.9
    do_sample: bool = True
    typical_p: float = 0.9
    repetition_penalty: float = 1.2
    encoder_repetition_penalty: float = 1.0
    min_length: int = 0
    no_repeat_ngram_size: int = 0
    num_beams: int = 1
    penalty_alpha: int = 0
    length_penalty: int = 1
    early_stopping: bool = False
    seed: int = -1
    add_bos_token: bool = True
    custom_stopping_strings: List[str] = ['### Assistant:']
    truncation_length: int = 2048
    ban_eos_token: bool = False


class LLM:
    def __init__(self, ip: str = "127.0.0.1", port: int = 5000):
        self.ip = ip
        self.port = port
        self.api_url = f"http://{self.ip}:{self.port}/api/v1/chat"

    def verify_port(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self.ip, self.port))
            s.close()
        except:
            return False
        return True

    def _unload_llm(self):
        response = requests.get(f"http://{self.ip}:{self.port}/api/v1/model", params={'action': 'unload'})
        if response.status_code == 200:
            return True
        else:
            return False

    # chat(params, add, filter, prompt_per_image)
    def chat(self, params: ChatParams, add: str = "", filter: str = "", prompts_per_image: int = 1, unload_after = False):
        results = []
        for i in range(prompts_per_image):
            response = self._send_request(params)
            if response:
                processed_text = self._process_text(params.user_input, response, add, filter)
                results.append(processed_text)
        if unload_after:
            logger.debug("We should unload the LLM here.")
            #self._unload_llm()
        return results

    def list_characters(self):
        defaults = ['if_ai_SD', 'iF_Ai_SD_b', 'iF_Ai_SD_NSFW']
        response = requests.get(f"http://{self.ip}:{self.port}/api/v1/characters")
        if response.status_code == 200:
            # Get the result from the response below and parse to a list, removing "None" and "Example"
            # {"result": ["None", "Example", "iF_Ai_SD_NSFW", "iF_Ai_SD_NSFW_bak"]}
            print(f"Got characters from LLM: {response.json()['result']}")
            characters = response.json()['result']
            characters = [x for x in characters if x != "None" and x != "Example"]
            return characters
        else:
            logger.warning(f"Failed to get characters from LLM: {response.status_code} - {response.text}")
            return defaults

    @staticmethod
    def comma_string_to_list(string: str):
        if "," in string:
            string = string.split(",")
        else:
            string = [string]
        string = [x.strip() for x in string]
        return string

    def _process_text(self, input: str, generated_text: str, add: str = "", filter: str = ""):
        # Filter audio stuff
        logger.debug("Processing generated text: " + generated_text)

        generated_text = generated_text.lower()
        if '<audio' in generated_text:
            logger.debug(f"Audio has been generated.")
            generated_text = re.sub(r'<audio.*?>.*?</audio>', '', generated_text)
        generated_text = ", ".join([input, generated_text])
        # Split our strings by commas
        generated_parts = self.comma_string_to_list(generated_text)
        add_words = self.comma_string_to_list(add)
        filter_words = self.comma_string_to_list(filter)

        # Filter out any words we don't want
        new_parts = []
        for g in generated_parts:
            if "(" in g and ")" not in g:
                continue
            parts = g.split() if " " in g else [g]
            for f in filter_words:
                if f in parts:
                    logger.debug(f"Filtering out generated text: {g}")
                    parts.remove(f)
            if len(parts):
                g = " ".join(parts)
                new_parts.append(g)

        # Add any words we want
        generated_test = ", ".join(new_parts)
        if len(add_words):
            for a in add_words:
                # If we're adding a word, make sure it's not already in the generated text
                if a not in generated_test:
                    new_parts.insert(0, a)

        # Remove duplicate entries from new_parts
        new_parts = list(dict.fromkeys(new_parts))

        # Join our final parts back together
        generated_text = ", ".join(new_parts)
        if generated_text == "":
            logger.warning(f"Generated text is empty, returning original text: {generated_text}")
        else:
            logger.debug(f"Returning generated text: {generated_text}")
        return generated_text

    def _send_request(self, data: ChatParams):
        headers = {"Content-Type": "application/json"}
        response = requests.post(self.api_url, data=json.dumps(data.__dict__), headers=headers)
        if response.status_code != 200:
            logger.warning(f"Request failed with status code {response.status_code}, check {self.api_url} and ensure LLM is running and properly configured.")
            return None

        results = json.loads(response.content)['results']
        if not results:
            print("No results found.")
            return None

        history = results[0]['history']
        if not history:
            return None

        visible = history['visible']
        if not visible:
            return None

        return visible[-1][1]


class PromptHelper:
    def __init__(self, llm_ip: str = "127.0.0.1", llm_port: int = 5000):
        self.llm_ip = llm_ip
        self.llm_port = llm_port
        self.llm = None
        self._init_llm()

    def _init_llm(self):
        self.llm = LLM(self.llm_ip, self.llm_port)
        if not self.llm.verify_port():
            logger.warning(f"LLM not running on {self.llm_ip}:{self.llm_port}")
            self.llm = None

    def improve_prompt(self, prompt: str, add: str = "", filter: str = "", prompt_per_image: int = 1,
                       character: str = "default", max_tokens: int = 150, unload_llm = False):
        params = ChatParams()
        params.user_input = prompt
        params.character = character
        params.max_new_tokens = max_tokens
        results = self.llm.chat(params, add, filter, prompt_per_image, unload_llm)
        return results
