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

def setup_agent() -> ReActAgent:
    guardrail = SecurityGuardrail(allowed_root=os.getcwd())
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(ReadFileTool(guardrail=guardrail))
    registry.register(WriteFileTool(guardrail=guardrail))
    registry.register(ExecuteCommandTool(guardrail=guardrail))

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        console.print("[bold green]✓[/bold green] [cyan]GeminiProvider[/cyan] loaded via GEMINI_API_KEY.")
        llm = GeminiProvider(api_key=api_key)
    else:
        console.print("[yellow]![/yellow] [bold yellow]GEMINI_API_KEY[/bold yellow] not found. Running in [bold cyan]Offline Demo Mode[/bold cyan].")
        console.print("  [dim]To use live Gemini models, set GEMINI_API_KEY environment variable.[/dim]\n")
        llm = OfflineMockProvider()

    memory = ConversationMemory(max_messages=15)
    return ReActAgent(llm=llm, tools=registry, memory=memory)

def main():
    console.print(Panel.fit(
        "[bold cyan]Task Automation Agent[/bold cyan] v0.1.0\n"
        "[dim]An autonomous ReAct-based agent for system tasks and QA[/dim]",
        border_style="cyan"
    ))

    agent = setup_agent()

    # Display available tools
    table = Table(title="Registered Tools", show_header=True, header_style="bold magenta")
    table.add_column("Tool Name", style="cyan", width=18)
    table.add_column("Description", style="white")
    for tool in agent.tools.get_all_tools():
        table.add_row(tool.name, tool.description)
    console.print(table)
    console.print("\nType your task/question below (type '[bold red]exit[/bold red]' or '[bold red]quit[/bold red]' to stop):\n")

    while True:
        try:
            user_input = console.input("[bold green]You > [/bold green]").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Exiting Task Agent. Goodbye![/yellow]")
                break

            with console.status("[cyan]Agent is reasoning and executing steps...[/cyan]", spinner="dots"):
                response = agent.run(user_input)

            # Display ReAct execution steps if any
            if response.steps:
                console.print("\n[bold blue]=== Execution Trace ===[/bold blue]")
                for idx, step in enumerate(response.steps, start=1):
                    step_content = (
                        f"[bold yellow]Thought:[/bold yellow] {step.thought}\n"
                        f"[bold magenta]Action:[/bold magenta] {step.action}({step.action_input})\n"
                        f"[bold green]Observation:[/bold green] {step.observation}"
                    )
                    console.print(Panel(step_content, title=f"Step {idx}", border_style="blue"))

            # Display Final Answer
            console.print(Panel(
                Markdown(response.final_answer),
                title="[bold green]Final Answer[/bold green]",
                border_style="green"
            ))
            console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]Session interrupted. Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")

if __name__ == "__main__":
    main()
