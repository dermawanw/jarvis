import gradio as gr
from brain import chat_turn, resolve_pending
from memory import index_vault, save_note
from skills import list_tasks

_voice = None


def get_voice():
    # shortcut: lazy-loads Whisper + Kokoro once globally for single-user local usage
    global _voice
    if _voice is None:
        import voice as voice_module
        _voice = voice_module
    return _voice


def handle_text(user_text: str, history: list[dict], pending: dict | None, speak_reply: bool = False):
    text = (user_text or "").strip()
    if pending is not None:
        msg = f"**Confirm or cancel first:** `{pending['name']}({pending['args']})`"
        return history, history, pending, user_text, gr.update(visible=True), msg, None, list_tasks()
    if not text:
        return history, history, None, "", gr.update(visible=False), "", None, list_tasks()

    new_history = list(history)
    if text.startswith("/remember "):
        path = save_note(text[10:])
        reply = f"Saved to {path}"
        new_history.extend([
            {"role": "user", "content": text},
            {"role": "assistant", "content": reply},
        ])
        return new_history, new_history, None, "", gr.update(visible=False), "", None, list_tasks()

    reply, new_pending = chat_turn(text, new_history, confirm_fn=None)
    if new_pending is not None:
        display = new_history + [
            {"role": "user", "content": text},
            {"role": "assistant", "content": reply},
        ]
        msg = f"**Pending:** `{new_pending['name']}({new_pending['args']})`"
        return display, new_history, new_pending, "", gr.update(visible=True), msg, None, list_tasks()

    audio = get_voice().synthesize(reply) if speak_reply else None
    return new_history, new_history, None, "", gr.update(visible=False), "", audio, list_tasks()


def handle_voice(audio_path: str | None, history: list[dict], pending: dict | None):
    if not audio_path:
        return history, history, pending, "", gr.update(visible=bool(pending)), "", None, list_tasks(), None
    text = get_voice().transcribe_file(audio_path)
    if not text:
        return history, history, pending, "", gr.update(visible=bool(pending)), "", None, list_tasks(), None
    out = handle_text(text, history, pending, speak_reply=True)
    return (*out, None)


def handle_confirm(approved: bool, history: list[dict], pending: dict | None):
    if pending is None:
        return history, history, None, gr.update(visible=False), "", list_tasks()
    new_history = list(history)
    resolve_pending(pending, approved, new_history)
    return new_history, new_history, None, gr.update(visible=False), "", list_tasks()


def do_reindex() -> str:
    return f"Indexed **{index_vault()}** chunks."


with gr.Blocks(title="JARVIS") as demo:
    history_state = gr.State([])
    pending_state = gr.State(None)

    gr.Markdown("# JARVIS (Local Offline)")

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(type="messages", height=440, label="Chat")

            with gr.Row(visible=False) as confirm_row:
                confirm_msg = gr.Markdown("")
                confirm_btn = gr.Button("Confirm", variant="primary", size="sm")
                cancel_btn = gr.Button("Cancel", variant="stop", size="sm")

            with gr.Row():
                msg_box = gr.Textbox(
                    placeholder="Ask JARVIS or type /remember <note>...",
                    show_label=False,
                    scale=5,
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)

            with gr.Row():
                mic = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label="Record voice, then click Send Voice",
                )
                voice_btn = gr.Button("Send Voice", scale=1)

            audio_out = gr.Audio(label="JARVIS Voice", autoplay=True)

        with gr.Column(scale=1):
            gr.Markdown("### Important Tasks")
            tasks_box = gr.Markdown(value=list_tasks)
            refresh_btn = gr.Button("Refresh Tasks", size="sm")
            reindex_btn = gr.Button("Reindex Obsidian", size="sm")
            status_box = gr.Markdown("")

    text_outputs = [
        chatbot,
        history_state,
        pending_state,
        msg_box,
        confirm_row,
        confirm_msg,
        audio_out,
        tasks_box,
    ]
    msg_box.submit(handle_text, [msg_box, history_state, pending_state], text_outputs)
    send_btn.click(handle_text, [msg_box, history_state, pending_state], text_outputs)
    voice_btn.click(
        handle_voice,
        [mic, history_state, pending_state],
        [*text_outputs, mic],
    )

    confirm_outputs = [
        chatbot,
        history_state,
        pending_state,
        confirm_row,
        confirm_msg,
        tasks_box,
    ]
    confirm_btn.click(
        lambda h, p: handle_confirm(True, h, p),
        [history_state, pending_state],
        confirm_outputs,
    )
    cancel_btn.click(
        lambda h, p: handle_confirm(False, h, p),
        [history_state, pending_state],
        confirm_outputs,
    )

    refresh_btn.click(list_tasks, outputs=tasks_box)
    reindex_btn.click(do_reindex, outputs=status_box)


if __name__ == "__main__":
    print(f"Indexed: {index_vault()} chunks.")
    # shortcut: localhost-only bind with no auth; add Gradio auth if ever exposed on LAN
    demo.launch(server_name="127.0.0.1", server_port=7860)