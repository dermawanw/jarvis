import ollama
from memory import index_vault, search, save_note
from skills import SKILLS, NEEDS_CONFIRM
from voice import listen, speak

CANCEL = "DIBATALKAN"
MODEL = "qwen3:8b"
SYSTEM = """Kamu adalah JARVIS, asisten pribadi Daniel.
Gunakan CATATAN jika relevan. Gunakan tools untuk waktu dan tugas.
Jangan mengarang hasil tool. Jawab singkat dan jujur."""

def run_tool(call):
    name, args = call.function.name, call.function.arguments or {}
    fn = SKILLS.get(name)
    if fn is None:
        return f"Tool '{name}' tidak ada."
    if name in NEEDS_CONFIRM:
        if input(f"  [izin] {name}({args})? (y/n) ").strip().lower() != "y":
            return CANCEL
    try:
        return str(fn(**args))
    except Exception as e:
        return f"Error: {e}"

history = [{"role": "system", "content": SYSTEM}]
print(f"Index: {index_vault()} chunk. Perintah: /ingat <teks>, /reindex, exit\n")

while True:
    user = input("Kamu > ").strip()
    spoken = False
    if user == "/v":
        user = listen()
        spoken = True
        print("Kamu (suara) >", user)
        if not user:
            continue
    if user.startswith("/ingat "):
        print("Disimpan ke", save_note(user[7:]), "\n"); continue
    if user == "/reindex":
        print("Index:", index_vault(), "chunk\n"); continue

    context = "\n---\n".join(f"[{s}]\n{d}" for d, s in search(user))
    msgs = history + [
        {"role": "system", "content": f"CATATAN:\n{context or '(kosong)'}"},
        {"role": "user", "content": user},
    ]

    cancelled = False
    for _ in range(5):
        r = ollama.chat(model=MODEL, messages=msgs,
                        tools=list(SKILLS.values()), think=False)
        msgs.append(r.message)
        if not r.message.tool_calls:
            break
        for call in r.message.tool_calls:
            print(f"  [tool] {call.function.name}({call.function.arguments})")
            result = run_tool(call)
            if result == CANCEL:
                cancelled = True
            msgs.append({"role": "tool", "content": result,
                         "tool_name": call.function.name})
        if cancelled:
            break   # jangan beri model kesempatan mengarang

    reply = "Oke, dibatalkan. Tidak ada yang diubah." if cancelled else r.message.content
    print("JARVIS >", reply, "\n")
    if spoken:
        speak(reply)
    history += [{"role": "user", "content": f"(suara) {user}" if spoken else user},
                {"role": "assistant", "content": reply}]