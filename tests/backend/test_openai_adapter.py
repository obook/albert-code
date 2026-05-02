from __future__ import annotations

from albert_code.core.config import Backend, ProviderConfig
from albert_code.core.llm.backend.generic import OpenAIAdapter


def _make_provider() -> ProviderConfig:
    return ProviderConfig(
        name="albert",
        api_base="http://test/v1",
        api_key_env_var="TEST_KEY",
        api_style="openai",
        backend=Backend.GENERIC,
    )


class TestOpenAIAdapterToolCallIndex:
    """Albert/vLLM emits native tool_calls without `index` (a streaming-only
    field). The adapter must assign sequential indexes so downstream
    accumulation does not raise "Tool call chunk missing index".
    """

    def test_assigns_index_when_missing(self) -> None:
        adapter = OpenAIAdapter()
        data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_a",
                                "type": "function",
                                "function": {"name": "read_file", "arguments": "{}"},
                            },
                            {
                                "id": "call_b",
                                "type": "function",
                                "function": {"name": "bash", "arguments": "{}"},
                            },
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        }

        chunk = adapter.parse_response(data, _make_provider())

        assert chunk.message.tool_calls is not None
        assert [tc.index for tc in chunk.message.tool_calls] == [0, 1]
        assert [tc.id for tc in chunk.message.tool_calls] == ["call_a", "call_b"]

    def test_preserves_existing_index(self) -> None:
        adapter = OpenAIAdapter()
        data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_a",
                                "index": 5,
                                "type": "function",
                                "function": {"name": "read_file", "arguments": "{}"},
                            }
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

        chunk = adapter.parse_response(data, _make_provider())

        assert chunk.message.tool_calls is not None
        assert chunk.message.tool_calls[0].index == 5

    def test_xml_tool_calls_already_have_index(self) -> None:
        """Sanity check: the existing XML extraction path keeps assigning indexes."""
        adapter = OpenAIAdapter()
        data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": (
                            "<tool_call><function=read_file>"
                            '<parameter=path>"foo.txt"</parameter>'
                            "</function></tool_call>"
                        ),
                    }
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

        chunk = adapter.parse_response(data, _make_provider())

        assert chunk.message.tool_calls is not None
        assert chunk.message.tool_calls[0].index == 0
        assert chunk.message.tool_calls[0].function.name == "read_file"

    def test_no_tool_calls_does_not_break(self) -> None:
        adapter = OpenAIAdapter()
        data = {
            "choices": [{"message": {"role": "assistant", "content": "hello"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

        chunk = adapter.parse_response(data, _make_provider())

        assert chunk.message.tool_calls is None
        assert chunk.message.content == "hello"
