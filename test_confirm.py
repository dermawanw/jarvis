from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import brain


def _fake_tool_response(name: str, args: dict):
    call = SimpleNamespace(function=SimpleNamespace(name=name, arguments=args))
    return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[call]))


def _fake_text_response(text: str):
    return SimpleNamespace(message=SimpleNamespace(content=text, tool_calls=None))


def test_confirm_gate():
    mock_add = MagicMock(return_value="Added: - [ ] test")
    mock_chat = MagicMock(return_value=_fake_tool_response("add_task", {"task": "test"}))
    with (
        patch.dict(brain.SKILLS, {"add_task": mock_add}),
        patch.object(brain, "search", return_value=[("RTX 4060", "Profile.md")]),
        patch.object(brain.ollama, "chat", mock_chat),
    ):
        hist = []
        reply, pending = brain.chat_turn("add task test", hist, confirm_fn=None)
        sent_msgs = mock_chat.call_args.kwargs["messages"]
        sys_msgs = [
            m for m in sent_msgs if isinstance(m, dict) and m.get("role") == "system"
        ]
        assert len(sys_msgs) == 1 and "NOTES:" in sys_msgs[0]["content"]
        assert pending is not None and pending["name"] == "add_task"
        assert "add_task" in reply
        mock_add.assert_not_called()

        cancel_reply = brain.resolve_pending(pending, approved=False, history=hist)
        assert cancel_reply == "Okay, cancelled. Nothing was changed."
        mock_add.assert_not_called()

        ok_hist = []
        ok_reply = brain.resolve_pending(pending, approved=True, history=ok_hist)
        assert "Added: - [ ] test" in ok_reply
        mock_add.assert_called_once_with(task="test")
        assert any("tool_calls" in m for m in ok_hist)
        assert any(m.get("role") == "tool" for m in ok_hist)

    # chat_turn menyimpan jejak tool_calls + tool response ke history
    mock_add.reset_mock()
    seq_chat = MagicMock(
        side_effect=[
            _fake_tool_response("add_task", {"task": "alpha"}),
            _fake_text_response("Added task: alpha."),
        ]
    )
    with (
        patch.dict(brain.SKILLS, {"add_task": mock_add}),
        patch.object(brain, "search", return_value=[]),
        patch.object(brain.ollama, "chat", seq_chat),
    ):
        multi_hist = []
        reply, pending = brain.chat_turn(
            "Add task alpha", multi_hist, confirm_fn=lambda *_: True
        )
        assert pending is None and "alpha" in reply
        assert [m["role"] for m in multi_hist] == ["user", "assistant", "tool", "assistant"]
        assert multi_hist[1]["tool_calls"][0]["function"]["name"] == "add_task"

    print("PASS: confirmation gate, single-system prompt, and tool history work.")


if __name__ == "__main__":
    test_confirm_gate()