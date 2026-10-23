from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel

class BaseTool(ABC):
    """Base class for all tools in Task Agent."""
    name: str
    description: str
    args_schema: Optional[Type[BaseModel]] = None

    @abstractmethod
    def run(self, **kwargs) -> str:
        """Execute the tool with given arguments and return a string result."""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Return the tool schema formatted for LLM consumption."""
        schema = {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
        if self.args_schema:
            pydantic_schema = self.args_schema.model_json_schema()
            schema["parameters"]["properties"] = pydantic_schema.get("properties", {})
            schema["parameters"]["required"] = pydantic_schema.get("required", [])
        return schema

class ToolRegistry:
    """Registry to manage and look up available tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def get_all_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_tools_description_prompt(self) -> str:
        """Generate formatted string of all tools for ReAct prompt."""
        lines = []
        for tool in self._tools.values():
            schema = tool.get_schema()
            props = schema["parameters"].get("properties", {})
            args_str = ", ".join(f"{k}: {v.get('type', 'any')}" for k, v in props.items())
            lines.append(f"- {tool.name}({args_str}): {tool.description}")
        return "\n".join(lines)
