import ollama
from memory import index_vault, search, save_note
from skills import SKILLS, NEEDS_CONFIRM

MODEL = "qwen3:8b"
CANCEL = "CANCELLED"
SYSTEM = """You are JARVIS, Daniel's personal assistant.
Use NOTES when relevant. Use tools for time and tasks.
Never make up tool results. Answer briefly and honestly.
If you don't know, say so."""

voice = None  # loaded on first /v


def run_tool(call):
    name, args = call.function.name, call.function.arguments or {}
    fn = SKILLS.get(name)
    if fn is None:
        return f"Tool '{name}' does not exist."
    if name in NEEDS_CONFIRM:
        if input(f"  [confirm] {name}({args})? (y/n) ").strip().lower() != "y":
            return CANCEL
    try:
        return str(fn(**args))
    except Exception as e:
        return f"Error: {e}"


history = [{"role": "system", "content": SYSTEM}]
print(f"Indexed: {index_vault()} chunks. Commands: /v (voice), /remember <text>, /reindex, exit\n")

while True:
    user = input("You > ").strip()
    if user.lower() in ("exit", "quit"):
        break
    if not user:
        continue
    if user.startswith("/remember "):
        print("Saved to", save_note(user[10:]), "\n")
        continue
    if user == "/reindex":
        print("Indexed:", index_vault(), "chunks\n")
        continue

    spoken = False
    if user == "/v":
        if voice is None:
            import voice as voice_module
            voice = voice_module
        user = voice.listen()
        spoken = True
        print("You (voice) >", user)
        if not user:
            continue

    context = "\n---\n".join(f"[{s}]\n{d}" for d, s in search(user))
    msgs = history + [
        {"role": "system", "content": f"NOTES:\n{context or '(empty)'}"},
        {"role": "user", "content": user},
    ]

    cancelled = False
    r = None
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
            break

    reply = "Okay, cancelled. Nothing was changed." if cancelled else (r.message.content or "")
    print("JARVIS >", reply, "\n")
    if spoken and voice is not None:
        voice.speak(reply)

    history += [{"role": "user", "content": user},
                {"role": "assistant", "content": reply}]