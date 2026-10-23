import pytest
import os
from pathlib import Path
from task_agent.tools.base import BaseTool, ToolRegistry
from task_agent.tools.system import ReadFileTool, WriteFileTool, ExecuteCommandTool, CalculatorTool
from task_agent.security.guardrails import SecurityGuardrail

def test_calculator_tool():
    tool = CalculatorTool()
    result = tool.run(expression="15 * 4 + 10")
    assert result == "70"

def test_calculator_invalid_expression():
    tool = CalculatorTool()
    result = tool.run(expression="__import__('os').system('dir')")
    assert "Error" in result

def test_file_tools(tmp_path: Path):
    guard = SecurityGuardrail(allowed_root=str(tmp_path))
    write_tool = WriteFileTool(guardrail=guard)
    read_tool = ReadFileTool(guardrail=guard)

    test_file = str(tmp_path / "hello.txt")
    write_result = write_tool.run(file_path=test_file, content="Hello, Agent!")
    assert "Success" in write_result

    read_result = read_tool.run(file_path=test_file)
    assert read_result == "Hello, Agent!"

def test_tool_registry():
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    
    assert "calculator" in registry.tool_names
    tool = registry.get_tool("calculator")
    assert tool is not None
    assert tool.name == "calculator"
    assert "expression" in tool.get_schema()["parameters"]["properties"]
