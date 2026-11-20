import os, datetime
from memory import VAULT, index_vault

TASKS = os.path.join(VAULT, "Important Tasks", "tasks.md")

def get_time() -> str:
    """Dapatkan tanggal dan jam sekarang."""
    return datetime.datetime.now().strftime("%A, %d %B %Y %H:%M")

def list_tasks() -> str:
    """Tampilkan semua tugas di daftar tugas Daniel."""
    if not os.path.exists(TASKS):
        return "Belum ada tugas."
    with open(TASKS, encoding="utf-8") as f:
        return f.read().strip() or "Belum ada tugas."

def add_task(task: str, due: str = "") -> str:
    """Tambahkan tugas baru ke daftar tugas.

    Args:
        task: deskripsi tugas
        due: tenggat waktu (opsional), contoh 28 November
    """
    os.makedirs(os.path.dirname(TASKS), exist_ok=True)
    line = f"- [ ] {task}" + (f" (due: {due})" if due else "")
    with open(TASKS, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    index_vault()
    return f"Ditambahkan: {line}"

SKILLS = {f.__name__: f for f in [get_time, list_tasks, add_task]}
NEEDS_CONFIRM = {"add_task"}   # aksi yang mengubah file wajib minta izin