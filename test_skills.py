import tempfile
from pathlib import Path
from unittest.mock import patch
import skills


def test_list_files_security():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp).resolve()
        (vault / "Projects").mkdir()
        (vault / "Projects" / "jarvis.md").write_text("hi", encoding="utf-8")
        (vault / ".obsidian").mkdir()
        (vault / ".obsidian" / "secret.md").write_text("cfg", encoding="utf-8")

        with patch.object(skills, "VAULT_PATH", vault):
            assert skills.list_files() == "Projects/jarvis.md"
            assert skills.list_files("Projects") == "Projects/jarvis.md"
            assert "Access denied" in skills.list_files("..")
            assert "Access denied" in skills.list_files("C:\\Windows")
            assert "Access denied" in skills.list_files(".obsidian")


def test_complete_task_matching():
    with tempfile.TemporaryDirectory() as tmp:
        tasks_file = Path(tmp) / "tasks.md"
        tasks_file.write_text(
            "- [ ] test dashboard (due: Nov 30)\n"
            "- [ ] test voice\n",
            encoding="utf-8",
        )

        with (
            patch.object(skills, "TASKS", str(tasks_file)),
            patch.object(skills, "index_vault", return_value=1),
        ):
            ambiguous = skills.complete_task("test")
            assert "Multiple open tasks" in ambiguous
            assert "- [x]" not in tasks_file.read_text(encoding="utf-8")

            ok = skills.complete_task("dashboard")
            assert ok.startswith("Completed:")
            content = tasks_file.read_text(encoding="utf-8")
            assert "- [x] test dashboard" in content
            assert "- [ ] test voice" in content

            again = skills.complete_task("dashboard")
            assert "No open task matching" in again


def test_write_tools_require_confirm():
    for name in ("add_task", "complete_task", "remember_note"):
        assert name in skills.NEEDS_CONFIRM


if __name__ == "__main__":
    test_list_files_security()
    test_complete_task_matching()
    test_write_tools_require_confirm()
    print("PASS: skills security & matching work.")