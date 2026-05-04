from __future__ import annotations

import json

from albert_code.core.llm.backend.generic import OpenAIAdapter, XmlToolCallStreamParser


def _make_parser() -> XmlToolCallStreamParser:
    return XmlToolCallStreamParser(OpenAIAdapter())


class TestXmlToolCallStreamParserPlainText:
    def test_passes_plain_text_through(self) -> None:
        parser = _make_parser()
        safe, calls = parser.feed("Hello world.")
        assert calls == []
        assert safe == "Hello world."

    def test_holds_back_partial_opening_tag(self) -> None:
        parser = _make_parser()
        # `<too` could be the start of `<tool_call>`: must not be emitted yet.
        safe, calls = parser.feed("answer <too")
        assert calls == []
        assert safe == "answer "

    def test_emits_held_back_partial_when_tag_completes(self) -> None:
        parser = _make_parser()
        parser.feed("answer <too")
        safe, calls = parser.feed("ls are great")
        # `<tools` is not the start of `<tool_call>`, so flush.
        assert calls == []
        assert safe == "<tools are great"


class TestXmlToolCallStreamParserStreamedToolCall:
    def test_parses_tool_call_split_across_many_chunks(self) -> None:
        """Reproduces the actual Albert SSE pattern: token-by-token."""
        parser = _make_parser()

        # Pattern observed against Albert/Qwen on /v1/chat/completions
        chunks = [
            "<tool_call>",
            "\n",
            "<",
            "function",
            "=read",
            "_file",
            ">\n",
            "<",
            "parameter",
            "=path",
            ">\n",
            "README",
            ".md",
            "\n",
            "</",
            "parameter",
            ">\n",
            "</",
            "function",
            ">\n",
            "</tool_call>",
        ]

        all_safe: list[str] = []
        all_calls: list = []
        for chunk in chunks:
            safe, calls = parser.feed(chunk)
            all_safe.append(safe)
            all_calls.extend(calls)

        assert "".join(all_safe).strip() == ""
        assert len(all_calls) == 1
        assert all_calls[0].function.name == "read_file"
        args = json.loads(all_calls[0].function.arguments or "{}")
        assert args == {"path": "README.md"}
        assert all_calls[0].index == 0

    def test_multiple_tool_calls_get_sequential_indexes(self) -> None:
        parser = _make_parser()
        block_1 = (
            "<tool_call>\n<function=foo>\n"
            "<parameter=x>1</parameter>\n</function>\n</tool_call>"
        )
        block_2 = (
            "<tool_call>\n<function=bar>\n"
            "<parameter=y>2</parameter>\n</function>\n</tool_call>"
        )
        safe_1, calls_1 = parser.feed(block_1)
        safe_2, calls_2 = parser.feed(block_2)
        assert calls_1[0].index == 0
        assert calls_2[0].index == 1
        assert safe_1.strip() == ""
        assert safe_2.strip() == ""

    def test_text_between_tool_calls_is_emitted(self) -> None:
        parser = _make_parser()
        text = (
            "Reading the README first.\n"
            "<tool_call>\n<function=read_file>\n"
            "<parameter=path>README.md</parameter>\n"
            "</function>\n</tool_call>\n"
            "Then I will summarize."
        )
        safe, calls = parser.feed(text)
        assert "Reading the README first." in safe
        assert "Then I will summarize." in safe
        assert len(calls) == 1
        assert calls[0].function.name == "read_file"


class TestXmlToolCallStreamParserFlush:
    def test_flush_recovers_truncated_tool_call(self) -> None:
        parser = _make_parser()
        # Stream cut mid-tool_call (no </tool_call>).
        parser.feed("<tool_call>\n<function=read_file>\n")
        parser.feed("<parameter=path>README.md</parameter>\n</function>")
        leftover_safe, leftover_calls = parser.flush()
        assert len(leftover_calls) == 1
        assert leftover_calls[0].function.name == "read_file"
        assert leftover_safe == ""

    def test_flush_empty_returns_nothing(self) -> None:
        parser = _make_parser()
        parser.feed("Hello")
        leftover_safe, leftover_calls = parser.flush()
        assert leftover_safe == ""
        assert leftover_calls == []


class TestXmlToolCallStreamParserBareFunction:
    """Coverage for Llama-style tool calls without `<tool_call>` wrapper.

    Some models (Llama 3.x, functionary, ...) emit tool calls with bare
    `<function=name>...</function>` tags, sometimes with a stray
    `</tool_call>` closing without a matching opening. The parser must
    extract these as tool calls rather than emit them as plain text.
    """

    def test_bare_function_block_in_single_chunk(self) -> None:
        parser = _make_parser()
        text = (
            "<function=write_file>"
            "<parameter=path>solution.py</parameter>"
            "<parameter=content>print(42)</parameter>"
            "</function>"
        )
        safe, calls = parser.feed(text)
        assert safe.strip() == ""
        assert len(calls) == 1
        assert calls[0].function.name == "write_file"
        args = json.loads(calls[0].function.arguments or "{}")
        assert args == {"path": "solution.py", "content": "print(42)"}

    def test_bare_function_split_across_chunks(self) -> None:
        parser = _make_parser()
        chunks = [
            "<function=",
            "write_file",
            ">",
            "<parameter=path>",
            "solution.py",
            "</parameter>",
            "<parameter=content>",
            "print(42)",
            "</parameter>",
            "</function>",
        ]
        all_safe: list[str] = []
        all_calls: list = []
        for chunk in chunks:
            safe, calls = parser.feed(chunk)
            all_safe.append(safe)
            all_calls.extend(calls)
        assert "".join(all_safe).strip() == ""
        assert len(all_calls) == 1
        assert all_calls[0].function.name == "write_file"

    def test_bare_function_closed_with_tool_call_only(self) -> None:
        """Malformed model output: missing `</function>`, only `</tool_call>`."""
        parser = _make_parser()
        text = (
            "<function=write_file>"
            "<parameter=path>solution.py</parameter>"
            "<parameter=content>print(42)</parameter>"
            "</tool_call>"
        )
        safe, calls = parser.feed(text)
        assert safe.strip() == ""
        assert len(calls) == 1
        assert calls[0].function.name == "write_file"

    def test_text_before_bare_function_is_emitted(self) -> None:
        parser = _make_parser()
        text = (
            "Voici le code demande :\n"
            "<function=write_file>"
            "<parameter=path>solution.py</parameter>"
            "<parameter=content>print(42)</parameter>"
            "</function>"
        )
        safe, calls = parser.feed(text)
        assert "Voici le code demande" in safe
        assert "<function=" not in safe
        assert len(calls) == 1

    def test_partial_function_open_held_back(self) -> None:
        parser = _make_parser()
        # `<func` could be the start of `<function=...>`: must not be emitted.
        safe, calls = parser.feed("answer <func")
        assert calls == []
        assert safe == "answer "

    def test_partial_function_open_released_when_no_match(self) -> None:
        parser = _make_parser()
        parser.feed("answer <func")
        safe, calls = parser.feed("tioning")
        assert calls == []
        assert safe == "<functioning"


class TestXmlToolCallStreamParserOrphanedClose:
    """Coverage for orphaned closing tags that leak into visible output.

    When the model emits <function=...>...</function></tool_call>, the parser
    grabs the inner <function> block first.  The leftover </tool_call> must
    be stripped rather than displayed to the user.
    """

    def test_orphaned_close_after_bare_function_same_chunk(self) -> None:
        parser = _make_parser()
        text = (
            "<function=read_file>"
            "<parameter=path>README.md</parameter>"
            "</function>"
            "\n</tool_call>"
        )
        safe, calls = parser.feed(text)
        assert "</tool_call>" not in safe
        assert safe.strip() == ""
        assert len(calls) == 1
        assert calls[0].function.name == "read_file"

    def test_orphaned_close_arrives_in_separate_chunk(self) -> None:
        parser = _make_parser()
        s1, c1 = parser.feed(
            "<function=read_file><parameter=path>README.md</parameter></function>"
        )
        s2, c2 = parser.feed("\n</tool_call>")
        assert len(c1) == 1
        assert "</tool_call>" not in s1
        assert "</tool_call>" not in s2

    def test_orphaned_close_split_across_chunks(self) -> None:
        """</tool_call> arrives as </to then ol_call>."""
        parser = _make_parser()
        parser.feed(
            "<function=read_file><parameter=path>README.md</parameter></function>"
        )
        s1, _ = parser.feed("</to")
        s2, _ = parser.feed("ol_call>")
        combined = s1 + s2
        assert "</tool_call>" not in combined
        assert combined.strip() == ""

    def test_orphaned_close_in_flush(self) -> None:
        parser = _make_parser()
        parser.feed(
            "<function=read_file><parameter=path>README.md</parameter></function>"
        )
        parser.feed("\n</tool_call>")
        leftover_safe, leftover_calls = parser.flush()
        assert "</tool_call>" not in leftover_safe

    def test_text_after_orphaned_close_is_preserved(self) -> None:
        parser = _make_parser()
        text = (
            "<function=read_file>"
            "<parameter=path>README.md</parameter>"
            "</function>"
            "</tool_call>"
            "Now I summarize."
        )
        safe, calls = parser.feed(text)
        assert "Now I summarize." in safe
        assert "</tool_call>" not in safe
        assert len(calls) == 1
