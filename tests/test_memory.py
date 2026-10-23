import pytest
from task_agent.core.memory import ConversationMemory, Message, Role

def test_add_and_retrieve_messages():
    memory = ConversationMemory(max_messages=5)
    memory.add_user_message("Hello")
    memory.add_assistant_message("Hi there! How can I help?")

    history = memory.get_messages()
    assert len(history) == 2
    assert history[0].role == Role.USER
    assert history[0].content == "Hello"
    assert history[1].role == Role.ASSISTANT

def test_memory_window_trimming():
    memory = ConversationMemory(max_messages=3)
    for i in range(5):
        memory.add_user_message(f"Message {i}")

    history = memory.get_messages()
    assert len(history) == 3
    assert history[0].content == "Message 2"
    assert history[-1].content == "Message 4"

def test_format_for_prompt():
    memory = ConversationMemory()
    memory.add_user_message("What is 2+2?")
    memory.add_assistant_message("4")

    formatted = memory.format_history_text()
    assert "User: What is 2+2?" in formatted
    assert "Assistant: 4" in formatted
