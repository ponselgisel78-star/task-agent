import re
import ast
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

from task_agent.core.memory import ConversationMemory
from task_agent.tools.base import ToolRegistry

class AgentStep(BaseModel):
    thought: str
    action: str
    action_input: Dict[str, Any]
    observation: str

class AgentResponse(BaseModel):
    final_answer: str
    steps: List[AgentStep] = Field(default_factory=list)

REACT_SYSTEM_PROMPT = """You are a smart Task Automation Agent. Solve the user's request step-by-step using available tools.

Available Tools:
{tools}

Always follow this strict format:
Thought: Describe your reasoning about what step to take.
Action: tool_name(arg_name="value", ...) [Only use tools from: {tool_names}]
Observation: The tool output will be provided here.
... (Repeat Thought -> Action -> Observation cycle as needed)
Thought: I have finished all actions and know the final answer.
Final Answer: Complete answer to the user's request.

If you already know the answer or no tools are required, respond directly with:
Thought: Reasoning why no tools are needed.
Final Answer: The final response.
"""

def parse_action_call(action_str: str) -> tuple[str, Dict[str, Any]]:
    """Safely parse tool_name(arg1="val", ...) using AST."""
    action_str = action_str.strip()
    match = re.match(r"^(\w+)\s*\((.*)\)$", action_str, re.DOTALL)
    if not match:
        # Just tool name without arguments
        return action_str, {}

    tool_name = match.group(1)
    args_str = match.group(2).strip()
    if not args_str:
        return tool_name, {}

    # Parse call using ast
    expr_code = f"func({args_str})"
    try:
        tree = ast.parse(expr_code, mode='eval')
        call_node = tree.body
        kwargs = {}
        for kw in call_node.keywords:
            # evaluate literal
            val = ast.literal_eval(kw.value)
            kwargs[kw.arg] = val
        return tool_name, kwargs
    except Exception:
        # Fallback keyword regex
        kwargs = {}
        kv_matches = re.findall(r'(\w+)\s*=\s*["\'](.*?)["\']', args_str)
        for k, v in kv_matches:
            kwargs[k] = v
        return tool_name, kwargs

class ReActAgent:
    """Autonomous ReAct agent coordinating LLM reasoning and tool execution."""

    def __init__(
        self,
        llm: Any,
        tools: Optional[ToolRegistry] = None,
        memory: Optional[ConversationMemory] = None,
        max_iterations: int = 8
    ):
        self.llm = llm
        self.tools = tools or ToolRegistry()
        self.memory = memory or ConversationMemory()
        self.max_iterations = max_iterations

    def run(self, user_query: str) -> AgentResponse:
        self.memory.add_user_message(user_query)
        tool_desc = self.tools.get_tools_description_prompt()
        tool_names = ", ".join(self.tools.tool_names)

        system_prompt = REACT_SYSTEM_PROMPT.format(
            tools=tool_desc if tool_desc else "(No tools available)",
            tool_names=tool_names if tool_names else "None"
        )

        steps: List[AgentStep] = []
        conversation_scratchpad = ""

        for iteration in range(self.max_iterations):
            prompt = (
                f"{system_prompt}\n\n"
                f"Conversation History:\n{self.memory.format_history_text()}\n\n"
                f"Current User Request: {user_query}\n"
                f"{conversation_scratchpad}\n"
            )

            llm_output = self.llm.generate(prompt).strip()

            # Check for Final Answer
            if "Final Answer:" in llm_output:
                parts = llm_output.split("Final Answer:", 1)
                final_answer = parts[1].strip()
                self.memory.add_assistant_message(final_answer)
                return AgentResponse(final_answer=final_answer, steps=steps)

            # Check for Thought & Action
            thought_match = re.search(r"Thought:(.*?)(?=Action:|$)", llm_output, re.DOTALL)
            thought = thought_match.group(1).strip() if thought_match else ""

            action_match = re.search(r"Action:(.*)", llm_output, re.DOTALL)
            if not action_match:
                # LLM didn't follow format, conclude with raw output
                self.memory.add_assistant_message(llm_output)
                return AgentResponse(final_answer=llm_output, steps=steps)

            action_line = action_match.group(1).strip().split("\n")[0]
            tool_name, tool_args = parse_action_call(action_line)

            # Execute Tool
            tool = self.tools.get_tool(tool_name)
            if not tool:
                observation = f"Error: Tool '{tool_name}' not found. Available tools: {tool_names}"
            else:
                try:
                    observation = tool.run(**tool_args)
                except Exception as e:
                    observation = f"Error executing tool '{tool_name}': {str(e)}"

            step = AgentStep(
                thought=thought,
                action=tool_name,
                action_input=tool_args,
                observation=observation
            )
            steps.append(step)

            # Append to scratchpad for next iteration
            conversation_scratchpad += (
                f"\nThought: {thought}\n"
                f"Action: {action_line}\n"
                f"Observation: {observation}\n"
            )

        # Exceeded iterations
        fallback_answer = f"Agent stopped: reached maximum iterations ({self.max_iterations}) without reaching a final answer."
        self.memory.add_assistant_message(fallback_answer)
        return AgentResponse(final_answer=fallback_answer, steps=steps)
