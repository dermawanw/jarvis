import os
import datetime
from memory import VAULT, index_vault

TASKS = os.path.join(VAULT, "Important Tasks", "tasks.md")


def get_time() -> str:
    """Get the current date and time."""
    return datetime.datetime.now().strftime("%A, %B %d %Y %H:%M")


def list_tasks() -> str:
    """List all of Daniel's tasks."""
    if not os.path.exists(TASKS):
        return "No tasks yet."
    with open(TASKS, encoding="utf-8") as f:
        return f.read().strip() or "No tasks yet."


def add_task(task: str, due: str = "") -> str:
    """Add a new task to Daniel's task list.

    Args:
        task: task description
        due: optional deadline, e.g. November 28
    """
    os.makedirs(os.path.dirname(TASKS), exist_ok=True)
    line = f"- [ ] {task}" + (f" (due: {due})" if due else "")
    with open(TASKS, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    index_vault()
    return f"Added: {line}"


SKILLS = {f.__name__: f for f in [get_time, list_tasks, add_task]}
NEEDS_CONFIRM = {"add_task"}