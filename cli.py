import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from task_agent.core.agent import ReActAgent
from task_agent.core.memory import ConversationMemory
from task_agent.tools.base import ToolRegistry
from task_agent.tools.system import (
    CalculatorTool,
    ReadFileTool,
    WriteFileTool,
    ExecuteCommandTool
)
from task_agent.security.guardrails import SecurityGuardrail
from task_agent.llm.provider import GeminiProvider, OfflineMockProvider

console = Console()

TOOL_KO_DESCRIPTIONS = {
    "calculator": "수학 수식(사칙연산, 거듭제곱 등)을 안전하게 계산",
    "read_file": "지정한 텍스트 파일의 내용 읽기",
    "write_file": "지정한 파일에 텍스트 내용 저장",
    "execute_command": "보안 검증을 거친 안전한 쉘 명령어 실행 및 결과 반환"
}

def setup_agent() -> ReActAgent:
    guardrail = SecurityGuardrail(allowed_root=os.getcwd())
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(ReadFileTool(guardrail=guardrail))
    registry.register(WriteFileTool(guardrail=guardrail))
    registry.register(ExecuteCommandTool(guardrail=guardrail))

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        console.print("[bold green]✓[/bold green] [cyan]GeminiProvider[/cyan] 온라인 모델 연결 완료 (GEMINI_API_KEY 적용됨).")
        llm = GeminiProvider(api_key=api_key)
    else:
        console.print("[yellow]![/yellow] [bold yellow]GEMINI_API_KEY[/bold yellow]가 설정되지 않아 [bold cyan]오프라인 데모 모드[/bold cyan]로 실행됩니다.")
        console.print("  [dim]실제 제미나이(Gemini) 모델을 연동하시려면 GEMINI_API_KEY 환경변수를 등록하세요.[/dim]\n")
        llm = OfflineMockProvider()

    memory = ConversationMemory(max_messages=15)
    return ReActAgent(llm=llm, tools=registry, memory=memory)

def main():
    console.print(Panel.fit(
        "[bold cyan]작업 자동화 AI 에이전트 (Task Automation Agent)[/bold cyan] v0.1.0\n"
        "[dim]ReAct 자율 추론 기반 시스템 제어 및 질의응답 봇[/dim]",
        border_style="cyan"
    ))

    agent = setup_agent()

    # 등록된 도구 목록 표시
    table = Table(title="사용 가능한 도구 목록 (Registered Tools)", show_header=True, header_style="bold magenta")
    table.add_column("도구 이름", style="cyan", width=18)
    table.add_column("기능 설명", style="white")
    for tool in agent.tools.get_all_tools():
        desc = TOOL_KO_DESCRIPTIONS.get(tool.name, tool.description)
        table.add_row(tool.name, desc)
    console.print(table)
    console.print("\n작업이나 질문을 입력하세요 (종료하려면 '[bold red]종료[/bold red]', '[bold red]exit[/bold red]', 또는 '[bold red]quit[/bold red]' 입력):\n")

    while True:
        try:
            user_input = console.input("[bold green]사용자 > [/bold green]").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q", "종료", "나가기"]:
                console.print("[yellow]에이전트를 종료합니다. 감사합니다![/yellow]")
                break

            with console.status("[cyan]에이전트가 생각하고 작업을 수행하는 중입니다...[/cyan]", spinner="dots"):
                response = agent.run(user_input)

            # ReAct 실행 단계 표시
            if response.steps:
                console.print("\n[bold blue]=== 작업 실행 과정 (ReAct Trace) ===[/bold blue]")
                for idx, step in enumerate(response.steps, start=1):
                    step_content = (
                        f"[bold yellow]생각 (Thought):[/bold yellow] {step.thought}\n"
                        f"[bold magenta]동작 (Action):[/bold magenta] {step.action}({step.action_input})\n"
                        f"[bold green]실행 결과 (Observation):[/bold green] {step.observation}"
                    )
                    console.print(Panel(step_content, title=f"단계 {idx}", border_style="blue"))

            # 최종 답변 표시
            console.print(Panel(
                Markdown(response.final_answer),
                title="[bold green]최종 답변 (Final Answer)[/bold green]",
                border_style="green"
            ))
            console.print()

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]세션이 중단되었습니다. 종료합니다.[/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]오류 발생:[/bold red] {str(e)}")

if __name__ == "__main__":
    main()
