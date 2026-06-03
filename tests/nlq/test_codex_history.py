from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mllo_web.app.api.services.codex_history import get_codex_chat_history


class CodexHistoryTests(unittest.TestCase):
    def test_history_filters_workspace_and_ignores_control_messages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            codex_home = Path(temp_dir)
            session_dir = codex_home / "sessions" / "2026" / "06" / "01"
            session_dir.mkdir(parents=True)
            session_id = "019e84e7-ffdc-74e2-9f72-51bb1f428836"
            session_path = session_dir / f"rollout-2026-06-01T16-37-37-{session_id}.jsonl"
            session_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "type": "session_meta",
                                "payload": {
                                    "id": session_id,
                                    "timestamp": "2026-06-01T20:37:37Z",
                                    "cwd": "/workspace/MLLO-Web-2",
                                },
                            }
                        ),
                        json.dumps(
                            {
                                "type": "response_item",
                                "payload": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [{"type": "input_text", "text": "<environment_context>hidden</environment_context>"}],
                                },
                            }
                        ),
                        json.dumps(
                            {
                                "type": "response_item",
                                "payload": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [{"type": "input_text", "text": "find chat history"}],
                                },
                            }
                        ),
                        json.dumps(
                            {
                                "type": "response_item",
                                "payload": {
                                    "type": "message",
                                    "role": "assistant",
                                    "content": [{"type": "output_text", "text": "I found the session files."}],
                                },
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            (codex_home / "session_index.jsonl").write_text(
                json.dumps(
                    {
                        "id": session_id,
                        "thread_name": "Find chat history",
                        "updated_at": "2026-06-01T20:38:09Z",
                    }
                ),
                encoding="utf-8",
            )

            with patch("pathlib.Path.cwd", return_value=Path("/workspace/MLLO-Web-2")):
                history = get_codex_chat_history(codex_home=codex_home)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["thread_name"], "Find chat history")
        self.assertEqual(history[0]["message_count"], 2)
        self.assertEqual(history[0]["first_user_message"], "find chat history")
        self.assertEqual(history[0]["last_assistant_message"], "I found the session files.")

    def test_query_filters_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            codex_home = Path(temp_dir)
            archive_dir = codex_home / "archived_sessions"
            archive_dir.mkdir(parents=True)
            session_id = "019e84e3-c199-78f1-bf2f-1ffbbc4c95c7"
            session_path = archive_dir / f"rollout-2026-06-01T16-32-59-{session_id}.jsonl"
            session_path.write_text(
                "\n".join(
                    [
                        json.dumps({"type": "session_meta", "payload": {"cwd": "/workspace/MLLO-Web-2"}}),
                        json.dumps(
                            {
                                "type": "response_item",
                                "payload": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [{"type": "input_text", "text": "add repo essentials"}],
                                },
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            (codex_home / "session_index.jsonl").write_text(
                json.dumps({"id": session_id, "thread_name": "Add repo essentials", "updated_at": "2026-06-01T20:33:29Z"}),
                encoding="utf-8",
            )

            with patch("pathlib.Path.cwd", return_value=Path("/workspace/MLLO-Web-2")):
                matching = get_codex_chat_history(query="repo", codex_home=codex_home)
                missing = get_codex_chat_history(query="graphdb", codex_home=codex_home)

        self.assertEqual(len(matching), 1)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
