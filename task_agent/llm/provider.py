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
                "GEMINI_API_KEY 환경변수가 설정되지 않았습니다. API 키를 등록해 주세요."
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
            raise RuntimeError(f"Gemini API 호출 오류 ({response.status_code}): {response.text}")

        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Gemini API 응답 데이터 구조 오류: {str(e)}")

class OfflineMockProvider(BaseLLMProvider):
    """Offline mock provider for testing and demonstration when no API key is available."""

    def __init__(self):
        self._counter = 0

    def generate(self, prompt: str) -> str:
        self._counter += 1
        prompt_lower = prompt.lower()

        # 도구 실행 결과(Observation)가 들어온 경우 -> 최종 한국어 답변 생성
        if "observation:" in prompt_lower or "관찰:" in prompt_lower:
            last_obs = prompt.split("Observation:")[-1].split("관찰:")[-1].split("\n")[0].strip()
            return f"Thought: 도구 실행 결과 '{last_obs}'를 확인했습니다. 사용자에게 최종 답변을 전달합니다.\nFinal Answer: 작업이 성공적으로 완료되었습니다.\n\n[실행 결과]:\n{last_obs}"

        # 수식 계산 요청
        if any(w in prompt_lower for w in ["calculate", "계산", "+", "*", "-", "/", "곱하기", "더하기", "빼기", "나누기"]):
            # 기본 수식 계산 도구 호출
            import re
            numbers = re.findall(r"[\d\s\+\-\*\/\(\)\.]+", prompt.split("[현재 사용자 요청]:")[-1])
            expr = numbers[0].strip() if numbers else "100 * 25 + 50"
            if not any(op in expr for op in ["+", "-", "*", "/"]):
                expr = "100 * 25 + 50"
            return f'Thought: 사용자가 수식 계산을 요청했습니다. 계산기 도구를 호출합니다.\nAction: calculator(expression="{expr}")'

        # 파일 읽기 요청
        elif any(w in prompt_lower for w in ["read", "읽어", "파일 확인", "readme"]):
            return 'Thought: 파일 내용을 확인해야 합니다. read_file 도구를 호출합니다.\nAction: read_file(file_path="README.md")'

        # 디렉터리 목록 또는 명령 실행
        elif any(w in prompt_lower for w in ["list", "dir", "목록", "파일들", "폴더", "상태"]):
            return 'Thought: 현재 폴더의 파일 목록을 확인하기 위해 execute_command 도구를 호출합니다.\nAction: execute_command(command="dir")'

        # 일반 인사 및 안내
        else:
            return 'Thought: 일반 대화이므로 별도의 도구 호출 없이 안내 답변을 제공합니다.\nFinal Answer: 안녕하세요! 작업 자동화 AI 에이전트입니다.\n\n수학 수식 계산, 파일 읽기/쓰기, 시스템 상태 점검 등의 작업을 요청하시면 단계별로 수행해 드립니다.'
