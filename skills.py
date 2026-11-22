import datetime
import os
from pathlib import Path
from memory import VAULT, index_vault, save_note, search

VAULT_PATH = Path(VAULT).resolve()
TASKS = os.path.join(VAULT, "Important Tasks", "tasks.md")


def _safe_vault_path(subpath: str) -> Path | None:
    clean = (subpath or "").strip()
    if not clean:
        return VAULT_PATH
    rel = Path(clean)
    if rel.is_absolute():
        return None
    target = (VAULT_PATH / rel).resolve()
    if not target.is_relative_to(VAULT_PATH):
        return None
    if ".obsidian" in target.relative_to(VAULT_PATH).parts:
        return None
    return target


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


def complete_task(keyword: str) -> str:
    """Mark an existing open task as done by matching a keyword.

    Args:
        keyword: unique word or phrase from the task to mark complete
    """
    kw = keyword.strip().lower()
    if not kw:
        return "Please provide a keyword to identify the task."
    if not os.path.exists(TASKS):
        return "No tasks yet."
    with open(TASKS, encoding="utf-8") as f:
        lines = f.readlines()

    matches = [
        i
        for i, line in enumerate(lines)
        if line.lstrip().startswith("- [ ]") and kw in line.lower()
    ]
    if not matches:
        return f"No open task matching '{keyword}'."
    if len(matches) > 1:
        # shortcut: refuses ambiguous matches instead of an interactive picker; revisit if task list grows large
        found = "\n".join(lines[i].strip() for i in matches)
        return f"Multiple open tasks match '{keyword}'. Be more specific:\n{found}"

    idx = matches[0]
    lines[idx] = lines[idx].replace("- [ ]", "- [x]", 1)
    with open(TASKS, "w", encoding="utf-8") as f:
        f.writelines(lines)
    index_vault()
    return f"Completed: {lines[idx].strip()}"


def search_notes(query: str) -> str:
    """Search Daniel's Obsidian notes for a specific topic or keyword.

    Args:
        query: search query
    """
    hits = search(query, k=5)
    if not hits:
        return "No matching notes found."
    return "\n---\n".join(f"[{src}]\n{doc}" for doc, src in hits)


def list_files(folder: str = "") -> str:
    """List markdown files inside the Obsidian vault or a subfolder.

    Args:
        folder: optional subfolder inside the vault, e.g. Projects
    """
    target = _safe_vault_path(folder)
    if target is None:
        return "Access denied: path must stay inside the vault."
    if not target.exists() or not target.is_dir():
        return f"Folder not found: {folder}"
    files = sorted(
        p.relative_to(VAULT_PATH).as_posix()
        for p in target.rglob("*.md")
        if ".obsidian" not in p.relative_to(VAULT_PATH).parts
    )
    return "\n".join(files) if files else "No markdown files found."


def remember_note(text: str) -> str:
    """Save a note to today's Daily Notes when Daniel explicitly asks to remember something.

    Args:
        text: note content to save
    """
    clean = text.strip()
    if not clean:
        return "Nothing to save."
    path = save_note(clean)
    return f"Saved to {Path(path).name}: {clean}"


SKILLS = {
    f.__name__: f
    for f in [
        get_time,
        list_tasks,
        add_task,
        complete_task,
        search_notes,
        list_files,
        remember_note,
    ]
}
NEEDS_CONFIRM = {"add_task", "complete_task", "remember_note"}