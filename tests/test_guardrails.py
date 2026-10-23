import pytest
from task_agent.security.guardrails import SecurityGuardrail, SecurityViolationError

def test_safe_command_allowed():
    guard = SecurityGuardrail()
    assert guard.validate_command("dir") == True
    assert guard.validate_command("echo Hello") == True
    assert guard.validate_command("python --version") == True

def test_destructive_command_blocked():
    guard = SecurityGuardrail()
    with pytest.raises(SecurityViolationError):
        guard.validate_command("rm -rf /")

    with pytest.raises(SecurityViolationError):
        guard.validate_command("format C:")

    with pytest.raises(SecurityViolationError):
        guard.validate_command("Remove-Item -Recurse -Force C:\\Windows")

def test_path_traversal_blocked():
    guard = SecurityGuardrail(allowed_root="C:\\safe_dir")
    with pytest.raises(SecurityViolationError):
        guard.validate_path("..\\..\\Windows\\System32\\cmd.exe")
