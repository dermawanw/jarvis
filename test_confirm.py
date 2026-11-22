from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import brain


def _fake_tool_response(name: str, args: dict):
    call = SimpleNamespace(function=SimpleNamespace(name=name, arguments=args))
    return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[call]))


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

        ok_reply = brain.resolve_pending(pending, approved=True, history=[])
        assert "Added: - [ ] test" in ok_reply
        mock_add.assert_called_once_with(task="test")

    print("PASS: confirmation gate and single-system prompt work.")


if __name__ == "__main__":
    test_confirm_gate()