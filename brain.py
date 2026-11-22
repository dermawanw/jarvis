import ollama
from memory import index_vault, search, save_note
from skills import SKILLS, NEEDS_CONFIRM

MODEL = "qwen3:8b"
SYSTEM = (
    "You are JARVIS, Daniel's personal assistant. "
    "Use NOTES when relevant. Use tools for time, tasks, searching or listing vault files, "
    "and saving notes only when Daniel explicitly asks to remember something. "
    "Never make up tool results. Answer briefly and honestly. "
    "If you don't know, say so."
)


def execute_tool(name: str, args: dict) -> str:
    fn = SKILLS.get(name)
    if fn is None:
        return f"Tool '{name}' does not exist."
    try:
        return str(fn(**args))
    except Exception as e:
        return f"Error: {e}"


def resolve_pending(pending: dict, approved: bool, history: list[dict]) -> str:
    if approved:
        result = execute_tool(pending["name"], pending["args"])
        reply = f"Done. {result}"
    else:
        reply = "Okay, cancelled. Nothing was changed."
    history.extend([
        {"role": "user", "content": pending["user"]},
        {"role": "assistant", "content": reply},
    ])
    return reply


def chat_turn(user: str, history: list[dict], confirm_fn=None) -> tuple[str, dict | None]:
    context = "\n---\n".join(f"[{s}]\n{d}" for d, s in search(user))
    msgs = [{"role": "system", "content": SYSTEM}] + history + [
        {"role": "system", "content": f"NOTES:\n{context or '(empty)'}"},
        {"role": "user", "content": user},
    ]

    r = None
    for _ in range(5):
        r = ollama.chat(
            model=MODEL,
            messages=msgs,
            tools=list(SKILLS.values()),
            think=False,
        )
        msgs.append(r.message)
        if not r.message.tool_calls:
            break
        for call in r.message.tool_calls:
            name = call.function.name
            args = dict(call.function.arguments or {})
            print(f"  [tool] {name}({args})")
            if name in NEEDS_CONFIRM:
                if confirm_fn is None:
                    # shortcut: pauses on first confirmable tool per turn; extend to a queue if multi-write skills are added
                    prompt = f"Confirm action: `{name}({args})`?"
                    return prompt, {"name": name, "args": args, "user": user}
                if not confirm_fn(name, args):
                    reply = "Okay, cancelled. Nothing was changed."
                    history.extend([
                        {"role": "user", "content": user},
                        {"role": "assistant", "content": reply},
                    ])
                    return reply, None
            result = execute_tool(name, args)
            msgs.append({
                "role": "tool",
                "content": result,
                "tool_name": name,
            })

    reply = (r.message.content or "") if r else ""
    history.extend([
        {"role": "user", "content": user},
        {"role": "assistant", "content": reply},
    ])
    return reply, None


def main():
    voice = None
    history: list[dict] = []
    chunks = index_vault()
    print(f"Indexed: {chunks} chunks. Commands: /v, /remember <text>, /reindex, exit\n")

    def cli_confirm(name: str, args: dict) -> bool:
        ans = input(f"  [confirm] {name}({args})? (y/n) ")
        return ans.strip().lower() == "y"

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

        reply, _ = chat_turn(user, history, confirm_fn=cli_confirm)
        print("JARVIS >", reply, "\n")
        if spoken and voice is not None:
            voice.speak(reply)


if __name__ == "__main__":
    main()