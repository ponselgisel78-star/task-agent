import ast
import operator
import subprocess
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from task_agent.tools.base import BaseTool
from task_agent.security.guardrails import SecurityGuardrail, SecurityViolationError

# Safe calculator using AST evaluation
_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def _eval_ast(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type}")
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        return _ALLOWED_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type}")
        operand = _eval_ast(node.operand)
        return _ALLOWED_OPERATORS[op_type](operand)
    else:
        raise ValueError(f"Unsupported expression element: {type(node)}")

class CalculatorInput(BaseModel):
    expression: str = Field(description="Math expression to calculate, e.g. '15 * 4 + 10'")

class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = "Safely evaluates mathematical expressions (add, sub, mul, div, pow, mod)."
    args_schema = CalculatorInput

    def run(self, expression: str, **kwargs) -> str:
        try:
            tree = ast.parse(expression, mode='eval')
            res = _eval_ast(tree.body)
            if isinstance(res, float) and res.is_integer():
                res = int(res)
            return str(res)
        except Exception as e:
            return f"Error evaluating expression: {str(e)}"

class ReadFileInput(BaseModel):
    file_path: str = Field(description="Path to the file to read")

class ReadFileTool(BaseTool):
    name: str = "read_file"
    description: str = "Reads the text content of a specified file."
    args_schema = ReadFileInput

    def __init__(self, guardrail: Optional[SecurityGuardrail] = None):
        self.guardrail = guardrail or SecurityGuardrail()

    def run(self, file_path: str, **kwargs) -> str:
        try:
            validated_path = self.guardrail.validate_path(file_path)
            if not validated_path.exists():
                return f"Error: File '{file_path}' does not exist."
            return validated_path.read_text(encoding="utf-8")
        except SecurityViolationError as sve:
            return f"Security Error: {str(sve)}"
        except Exception as e:
            return f"Error reading file: {str(e)}"

class WriteFileInput(BaseModel):
    file_path: str = Field(description="Path to the file to write")
    content: str = Field(description="Text content to write into the file")

class WriteFileTool(BaseTool):
    name: str = "write_file"
    description: str = "Writes text content to a specified file."
    args_schema = WriteFileInput

    def __init__(self, guardrail: Optional[SecurityGuardrail] = None):
        self.guardrail = guardrail or SecurityGuardrail()

    def run(self, file_path: str, content: str, **kwargs) -> str:
        try:
            validated_path = self.guardrail.validate_path(file_path)
            validated_path.parent.mkdir(parents=True, exist_ok=True)
            validated_path.write_text(content, encoding="utf-8")
            return f"Success: File '{file_path}' written successfully ({len(content)} chars)."
        except SecurityViolationError as sve:
            return f"Security Error: {str(sve)}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

class ExecuteCommandInput(BaseModel):
    command: str = Field(description="Shell command to execute")

class ExecuteCommandTool(BaseTool):
    name: str = "execute_command"
    description: str = "Executes an authorized shell command and returns output."
    args_schema = ExecuteCommandInput

    def __init__(self, guardrail: Optional[SecurityGuardrail] = None, timeout: int = 15):
        self.guardrail = guardrail or SecurityGuardrail()
        self.timeout = timeout

    def run(self, command: str, **kwargs) -> str:
        try:
            self.guardrail.validate_command(command)
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            out = proc.stdout if proc.stdout else ""
            err = proc.stderr if proc.stderr else ""
            return f"Exit Code: {proc.returncode}\nOutput:\n{out}\nError:\n{err}".strip()
        except SecurityViolationError as sve:
            return f"Security Error: {str(sve)}"
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {self.timeout}s."
        except Exception as e:
            return f"Error executing command: {str(e)}"
