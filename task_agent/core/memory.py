from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class Message(BaseModel):
    role: Role
    content: str
    metadata: Optional[dict] = Field(default_factory=dict)

class ConversationMemory:
    """Manages conversational context with rolling window pruning."""

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self._messages: List[Message] = []

    def add_message(self, role: Role, content: str, metadata: Optional[dict] = None) -> None:
        self._messages.append(Message(role=role, content=content, metadata=metadata or {}))
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages:]

    def add_user_message(self, content: str) -> None:
        self.add_message(Role.USER, content)

    def add_assistant_message(self, content: str) -> None:
        self.add_message(Role.ASSISTANT, content)

    def add_system_message(self, content: str) -> None:
        self.add_message(Role.SYSTEM, content)

    def get_messages(self) -> List[Message]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def format_history_text(self) -> str:
        """Format history for text-based prompts."""
        lines = []
        for msg in self._messages:
            role_label = msg.role.value.capitalize()
            lines.append(f"{role_label}: {msg.content}")
        return "\n".join(lines)
