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

REACT_SYSTEM_PROMPT = """당신은 스마트 작업 자동화 AI 에이전트(Task Automation Agent)입니다. 사용자의 요청을 단계별로 분석하고 사용 가능한 도구(Tools)를 활용하여 해결하세요.

사용 가능한 도구 목록:
{tools}

반드시 아래 형식에 맞추어 응답해야 합니다:
Thought: 다음으로 수행할 작업에 대한 논리적 추론 및 계획을 한국어로 작성합니다.
Action: tool_name(arg_name="값", ...) [사용 가능한 도구: {tool_names}]
Observation: 도구 실행 결과가 여기에 제공됩니다.
... (필요한 만큼 Thought -> Action -> Observation 단계를 반복)
Thought: 모든 작업을 완료했거나 결과를 도출했습니다.
Final Answer: 사용자의 원래 질문이나 요청에 대한 완성된 최종 한국어 답변.

도구를 사용할 필요가 없거나 이미 답을 알고 있는 경우:
Thought: 도구가 필요하지 않은 이유.
Final Answer: 사용자에게 전달할 최종 한국어 답변.
"""

def parse_action_call(action_str: str) -> tuple[str, Dict[str, Any]]:
    """Safely parse tool_name(arg1="val", ...) using AST."""
    action_str = action_str.strip()
    match = re.match(r"^(\w+)\s*\((.*)\)$", action_str, re.DOTALL)
    if not match:
        return action_str, {}

    tool_name = match.group(1)
    args_str = match.group(2).strip()
    if not args_str:
        return tool_name, {}

    expr_code = f"func({args_str})"
    try:
        tree = ast.parse(expr_code, mode='eval')
        call_node = tree.body
        kwargs = {}
        for kw in call_node.keywords:
            val = ast.literal_eval(kw.value)
            kwargs[kw.arg] = val
        return tool_name, kwargs
    except Exception:
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
            tools=tool_desc if tool_desc else "(사용 가능한 도구 없음)",
            tool_names=tool_names if tool_names else "없음"
        )

        steps: List[AgentStep] = []
        conversation_scratchpad = ""

        for iteration in range(self.max_iterations):
            prompt = (
                f"{system_prompt}\n\n"
                f"[이전 대화 기록]\n{self.memory.format_history_text()}\n\n"
                f"[현재 사용자 요청]: {user_query}\n"
                f"{conversation_scratchpad}\n"
            )

            llm_output = self.llm.generate(prompt).strip()

            # Check for Final Answer (Korean or English)
            final_marker = None
            if "Final Answer:" in llm_output:
                final_marker = "Final Answer:"
            elif "최종 답변:" in llm_output:
                final_marker = "최종 답변:"

            if final_marker:
                parts = llm_output.split(final_marker, 1)
                final_answer = parts[1].strip()
                self.memory.add_assistant_message(final_answer)
                return AgentResponse(final_answer=final_answer, steps=steps)

            # Check for Thought & Action
            thought_match = re.search(r"(?:Thought|생각):(.*?)(?=(?:Action|행동):|$)", llm_output, re.DOTALL)
            thought = thought_match.group(1).strip() if thought_match else ""

            action_match = re.search(r"(?:Action|행동):(.*)", llm_output, re.DOTALL)
            if not action_match:
                self.memory.add_assistant_message(llm_output)
                return AgentResponse(final_answer=llm_output, steps=steps)

            action_line = action_match.group(1).strip().split("\n")[0]
            tool_name, tool_args = parse_action_call(action_line)

            # Execute Tool
            tool = self.tools.get_tool(tool_name)
            if not tool:
                observation = f"오류: '{tool_name}' 도구를 찾을 수 없습니다. (사용 가능 도구: {tool_names})"
            else:
                try:
                    observation = tool.run(**tool_args)
                except Exception as e:
                    observation = f"도구 실행 오류 ({tool_name}): {str(e)}"

            step = AgentStep(
                thought=thought,
                action=tool_name,
                action_input=tool_args,
                observation=observation
            )
            steps.append(step)

            conversation_scratchpad += (
                f"\nThought: {thought}\n"
                f"Action: {action_line}\n"
                f"Observation: {observation}\n"
            )

        fallback_answer = f"에이전트 중단: 최대 반복 횟수 도달(Reached maximum iterations, {self.max_iterations}회)하여 종료되었습니다."
        self.memory.add_assistant_message(fallback_answer)
        return AgentResponse(final_answer=fallback_answer, steps=steps)
