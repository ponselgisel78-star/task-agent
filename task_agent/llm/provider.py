import os
import requests
from abc import ABC, abstractmethod
from typing import Optional

class BaseLLMProvider(ABC):
    """Abstract interface for LLM calls."""
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Takes a prompt string and returns completion text."""
        pass

class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider using REST API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set the GEMINI_API_KEY environment variable or pass api_key."
            )
        self.model = model
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        )

    def generate(self, prompt: str) -> str:
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048
            }
        }
        response = requests.post(self.endpoint, json=payload, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"Gemini API error ({response.status_code}): {response.text}")

        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected response structure from Gemini API: {str(e)}")

class OfflineMockProvider(BaseLLMProvider):
    """Offline mock provider for testing and demonstration when no API key is available."""

    def __init__(self):
        self._counter = 0

    def generate(self, prompt: str) -> str:
        self._counter += 1
        prompt_lower = prompt.lower()

        # If scratchpad has observation, finalize answer
        if "observation:" in prompt_lower:
            # extract observation
            last_obs = prompt.split("Observation:")[-1].split("\n")[0].strip()
            return f"Thought: I received the observation '{last_obs}'. Now I can provide the final answer.\nFinal Answer: Task completed successfully. Result: {last_obs}"

        # Simple intent routing
        if "calculate" in prompt_lower or "+" in prompt_lower or "*" in prompt_lower:
            # extract potential math
            return 'Thought: The user requested a calculation. I will use the calculator tool.\nAction: calculator(expression="100 * 25 + 50")'
        elif "read" in prompt_lower:
            return 'Thought: I need to read the requested file.\nAction: read_file(file_path="README.md")'
        elif "list" in prompt_lower or "dir" in prompt_lower:
            return 'Thought: I will list files in the current directory.\nAction: execute_command(command="dir")'
        else:
            return 'Thought: General query with no tool needed.\nFinal Answer: Hello! I am your Task Automation Agent. You can ask me to calculate math, read/write files, or execute safe system commands.'
