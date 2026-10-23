import pytest
from task_agent.core.agent import ReActAgent, AgentStep, AgentResponse
from task_agent.core.memory import ConversationMemory
from task_agent.tools.base import ToolRegistry
from task_agent.tools.system import CalculatorTool

class MockLLMProvider:
    """Mock LLM provider returning predetermined sequence of responses."""
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.prompts_received = []

    def generate(self, prompt: str) -> str:
        self.prompts_received.append(prompt)
        if not self.responses:
            return "Final Answer: No more responses configured."
        return self.responses.pop(0)

def test_react_agent_single_tool_execution():
    tool_registry = ToolRegistry()
    tool_registry.register(CalculatorTool())
    memory = ConversationMemory()

    mock_llm = MockLLMProvider([
        'Thought: I need to calculate 15 * 4.\nAction: calculator(expression="15 * 4")',
        'Thought: The result is 60.\nFinal Answer: 15 * 4 is 60.'
    ])

    agent = ReActAgent(
        llm=mock_llm,
        tools=tool_registry,
        memory=memory,
        max_iterations=5
    )

    response = agent.run("Calculate 15 * 4")
    assert response.final_answer == "15 * 4 is 60."
    assert len(response.steps) == 1
    assert response.steps[0].action == "calculator"
    assert response.steps[0].observation == "60"

def test_react_agent_direct_answer_without_tools():
    tool_registry = ToolRegistry()
    mock_llm = MockLLMProvider([
        'Thought: This is a greeting, no tools needed.\nFinal Answer: Hello! How can I assist you today?'
    ])

    agent = ReActAgent(
        llm=mock_llm,
        tools=tool_registry
    )

    response = agent.run("Hello")
    assert response.final_answer == "Hello! How can I assist you today?"
    assert len(response.steps) == 0

def test_react_agent_max_iterations_limit():
    tool_registry = ToolRegistry()
    tool_registry.register(CalculatorTool())
    
    # Infinite loop mock responses
    mock_llm = MockLLMProvider([
        'Thought: Thinking...\nAction: calculator(expression="1+1")',
        'Thought: Thinking again...\nAction: calculator(expression="1+1")',
        'Thought: Thinking again...\nAction: calculator(expression="1+1")'
    ])

    agent = ReActAgent(
        llm=mock_llm,
        tools=tool_registry,
        max_iterations=2
    )

    response = agent.run("Loop test")
    assert "reached maximum iterations" in response.final_answer.lower()
