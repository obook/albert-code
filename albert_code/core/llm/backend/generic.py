from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator, Sequence
import datetime as dt
import email.utils
import json
import logging
import os
import re
import types
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

HTTP_TOO_MANY_REQUESTS = 429

from albert_code.core.llm.backend.anthropic import AnthropicAdapter
from albert_code.core.llm.backend.base import APIAdapter, PreparedRequest
from albert_code.core.llm.backend.vertex import VertexAnthropicAdapter
from albert_code.core.llm.exceptions import BackendErrorBuilder, TerminalRateLimitError
from albert_code.core.llm.message_utils import merge_consecutive_user_messages
from albert_code.core.llm.throttling import get_throttler
from albert_code.core.types import (
    AvailableTool,
    FunctionCall,
    LLMChunk,
    LLMMessage,
    LLMUsage,
    Role,
    StrToolChoice,
    ToolCall,
)
from albert_code.core.utils import async_generator_retry, async_retry

if TYPE_CHECKING:
    from albert_code.core.config import ModelConfig, ProviderConfig


class OpenAIAdapter(APIAdapter):
    endpoint: ClassVar[str] = "/chat/completions"

    def build_payload(
        self,
        model_name: str,
        converted_messages: list[dict[str, Any]],
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | AvailableTool | None,
    ) -> dict[str, Any]:
        payload = {
            "model": model_name,
            "messages": converted_messages,
            "temperature": temperature,
        }

        if tools:
            payload["tools"] = [tool.model_dump(exclude_none=True) for tool in tools]
        if tool_choice:
            payload["tool_choice"] = (
                tool_choice
                if isinstance(tool_choice, str)
                else tool_choice.model_dump()
            )
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        return payload

    def build_headers(self, api_key: str | None = None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _reasoning_to_api(
        self, msg_dict: dict[str, Any], field_name: str
    ) -> dict[str, Any]:
        if field_name != "reasoning_content" and "reasoning_content" in msg_dict:
            msg_dict[field_name] = msg_dict.pop("reasoning_content")
        return msg_dict

    def _reasoning_from_api(
        self, msg_dict: dict[str, Any], field_name: str
    ) -> dict[str, Any]:
        if field_name != "reasoning_content" and field_name in msg_dict:
            msg_dict["reasoning_content"] = msg_dict.pop(field_name)
        return msg_dict

    def prepare_request(  # noqa: PLR0913
        self,
        *,
        model_name: str,
        messages: Sequence[LLMMessage],
        temperature: float,
        tools: list[AvailableTool] | None,
        max_tokens: int | None,
        tool_choice: StrToolChoice | AvailableTool | None,
        enable_streaming: bool,
        provider: ProviderConfig,
        api_key: str | None = None,
        thinking: str = "off",
    ) -> PreparedRequest:
        merged_messages = merge_consecutive_user_messages(messages)
        field_name = provider.reasoning_field_name
        converted_messages = [
            self._reasoning_to_api(
                msg.model_dump(exclude_none=True, exclude={"message_id"}), field_name
            )
            for msg in merged_messages
        ]

        if tools and provider.tool_choice_override:
            tool_choice = provider.tool_choice_override  # type: ignore[assignment]

        payload = self.build_payload(
            model_name, converted_messages, temperature, tools, max_tokens, tool_choice
        )

        if enable_streaming:
            payload["stream"] = True
            stream_options = {"include_usage": True}
            if provider.name == "mistral":
                stream_options["stream_tool_calls"] = True
            payload["stream_options"] = stream_options

        headers = self.build_headers(api_key)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        return PreparedRequest(self.endpoint, headers, body)

    def _parse_message(
        self, data: dict[str, Any], field_name: str
    ) -> LLMMessage | None:
        if data.get("choices"):
            choice = data["choices"][0]
            if "message" in choice:
                msg_dict = self._reasoning_from_api(choice["message"], field_name)
                return LLMMessage.model_validate(msg_dict)
            if "delta" in choice:
                msg_dict = self._reasoning_from_api(choice["delta"], field_name)
                return LLMMessage.model_validate(msg_dict)
            raise ValueError("Invalid response data: missing message or delta")

        if "message" in data:
            msg_dict = self._reasoning_from_api(data["message"], field_name)
            return LLMMessage.model_validate(msg_dict)
        if "delta" in data:
            msg_dict = self._reasoning_from_api(data["delta"], field_name)
            return LLMMessage.model_validate(msg_dict)

        return None

    # Matches <function=name>...</function> with optional <tool_call> wrapper.
    # Also handles truncated responses where </function> may be missing.
    _TOOL_CALL_RE = re.compile(
        r"(?:<tool_call>\s*)?<function=(\w+)>(.*?)(?:</function>(?:\s*</tool_call>)?|$)",
        re.DOTALL,
    )
    _PARAM_RE = re.compile(
        r"<parameter=(\w+)>(.*?)(?:</parameter>|(?=<parameter=)|$)", re.DOTALL
    )

    def _extract_xml_tool_calls(
        self, content: str, *, start_index: int = 0
    ) -> tuple[str, list[ToolCall]]:
        """Extract Qwen-style XML tool calls from content.

        Returns the cleaned content and a list of ToolCall objects.
        Tool call indexes start at `start_index` (default 0).
        """
        tool_calls: list[ToolCall] = []

        for offset, match in enumerate(self._TOOL_CALL_RE.finditer(content)):
            func_name = match.group(1)
            body = match.group(2)
            params: dict[str, Any] = {}
            for pm in self._PARAM_RE.finditer(body):
                raw = pm.group(2).strip()
                try:
                    params[pm.group(1)] = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    params[pm.group(1)] = raw
            tool_calls.append(
                ToolCall(
                    id=f"tc-{uuid4().hex[:12]}",
                    index=start_index + offset,
                    function=FunctionCall(
                        name=func_name, arguments=json.dumps(params, ensure_ascii=False)
                    ),
                )
            )
        cleaned = self._TOOL_CALL_RE.sub("", content).strip()
        # Strip trailing incomplete tags
        cleaned = re.sub(
            r"<(?:tool_call|function=\w+|/function|/tool_call)[^>]*>\s*$", "", cleaned
        ).strip()
        return cleaned, tool_calls

    def parse_response(
        self, data: dict[str, Any], provider: ProviderConfig
    ) -> LLMChunk:
        message = self._parse_message(data, provider.reasoning_field_name)
        if message is None:
            message = LLMMessage(role=Role.assistant, content="")

        # Streaming chunks contain `delta`, not `message`. We skip the bulk XML
        # extraction here because each delta only carries a fragment; a
        # dedicated incremental parser handles streaming reliably (see
        # XmlToolCallStreamParser used by complete_streaming).
        choices = data.get("choices") or []
        is_streaming_chunk = bool(choices) and "delta" in choices[0]

        if not is_streaming_chunk:
            # Extract XML tool calls from content for providers that emit them
            # (e.g. Qwen models on vLLM with tool_choice=auto, non-streaming).
            content_str = str(message.content) if message.content else ""
            if (
                content_str
                and not message.tool_calls
                and ("<tool_call>" in content_str or "<function=" in content_str)
            ):
                cleaned, xml_tool_calls = self._extract_xml_tool_calls(content_str)
                update: dict[str, Any] = {"content": cleaned or None}
                if xml_tool_calls:
                    update["tool_calls"] = xml_tool_calls
                message = message.model_copy(update=update)

        # Non-streaming responses do not include `index` on tool_calls (it is a
        # streaming-only field per OpenAI spec). Albert/vLLM may emit native
        # tool_calls without index; downstream accumulation requires one.
        if message.tool_calls:
            for idx, tc in enumerate(message.tool_calls):
                if tc.index is None:
                    tc.index = idx

        usage_data = data.get("usage") or {}
        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
        )

        return LLMChunk(message=message, usage=usage)


ADAPTERS: dict[str, APIAdapter] = {
    "openai": OpenAIAdapter(),
    "anthropic": AnthropicAdapter(),
    "vertex-anthropic": VertexAnthropicAdapter(),
}


_TOOL_CALL_OPEN = "<tool_call>"
_TOOL_CALL_CLOSE = "</tool_call>"
_FN_OPEN_PREFIX = "<function="
_FN_CLOSE = "</function>"
_FN_OPEN_RE = re.compile(r"<function=\w+>")
# Trailing fragment that could be the start of `<function=name>` once more
# text arrives. Matches `<`, `<f`, ..., `<function`, `<function=`, `<function=foo`.
_FN_OPEN_PARTIAL_RE = re.compile(
    r"<(?:f(?:u(?:n(?:c(?:t(?:i(?:o(?:n(?:=\w*)?)?)?)?)?)?)?)?)?$"
)


class XmlToolCallStreamParser:
    """Incremental parser for XML-style tool calls in a streamed content.

    Albert/vLLM emits tool calls as XML inside `delta.content`, split across
    many small SSE chunks (e.g. `<tool_call>`, `\\n`, `<`, `function`,
    `=read`, `_file`, `>`, ...). The parser also handles the bare
    `<function=name>...</function>` form emitted by Llama-style models,
    even when the `<tool_call>` wrapper is missing or malformed.

    The parser accumulates a buffer, yields only the text that is safe to
    display (i.e. text not inside a tool call, and not the trailing fragment
    of a partial opening tag), and emits `ToolCall` objects whenever a
    complete tool call block is received.
    """

    def __init__(self, adapter: OpenAIAdapter) -> None:
        self._adapter = adapter
        self._buffer = ""
        self._next_tool_index = 0

    def feed(self, delta: str) -> tuple[str, list[ToolCall]]:
        """Consume a delta. Returns (safe_content_to_emit, completed_tool_calls)."""
        if not delta:
            return "", []
        self._buffer += delta
        return self._drain()

    def flush(self) -> tuple[str, list[ToolCall]]:
        """End of stream: emit anything still buffered, including partial tool calls."""
        leftover = self._buffer
        self._buffer = ""
        if not leftover:
            return "", []
        if _TOOL_CALL_OPEN in leftover or _FN_OPEN_PREFIX in leftover:
            cleaned, tool_calls = self._adapter._extract_xml_tool_calls(
                leftover, start_index=self._next_tool_index
            )
            self._next_tool_index += len(tool_calls)
            return cleaned, tool_calls
        return leftover, []

    def _find_open(self) -> tuple[int, str]:
        """Earliest opening marker as (index, kind). Returns (-1, '') if none.

        `kind` is either 'tc' (`<tool_call>`) or 'fn' (`<function=...>`).
        """
        tc_open = self._buffer.find(_TOOL_CALL_OPEN)
        fn_match = _FN_OPEN_RE.search(self._buffer)
        fn_open = fn_match.start() if fn_match else -1
        candidates = []
        if tc_open >= 0:
            candidates.append((tc_open, "tc"))
        if fn_open >= 0:
            candidates.append((fn_open, "fn"))
        return min(candidates) if candidates else (-1, "")

    def _find_close(self, open_kind: str, after: int) -> tuple[int, int]:
        """Earliest matching close marker after `after`. Returns (idx, length).

        For `<tool_call>` openers, only `</tool_call>` is accepted. For bare
        `<function=...>` openers, either `</function>` or `</tool_call>` is
        accepted (whichever comes first), to tolerate malformed model output.
        """
        if open_kind == "tc":
            idx = self._buffer.find(_TOOL_CALL_CLOSE, after)
            return (idx, len(_TOOL_CALL_CLOSE)) if idx >= 0 else (-1, 0)
        fn_close_idx = self._buffer.find(_FN_CLOSE, after)
        tc_close_idx = self._buffer.find(_TOOL_CALL_CLOSE, after)
        candidates = []
        if fn_close_idx >= 0:
            candidates.append((fn_close_idx, len(_FN_CLOSE)))
        if tc_close_idx >= 0:
            candidates.append((tc_close_idx, len(_TOOL_CALL_CLOSE)))
        return min(candidates) if candidates else (-1, 0)

    def _trailing_partial_open_length(self) -> int:
        """Length of the trailing fragment that could be the start of an opener."""
        tc_partial = _partial_tag_suffix_length(self._buffer, _TOOL_CALL_OPEN)
        fn_match = _FN_OPEN_PARTIAL_RE.search(self._buffer)
        fn_partial = (
            len(self._buffer) - fn_match.start() if fn_match and fn_match.group() else 0
        )
        return max(tc_partial, fn_partial)

    def _drain(self) -> tuple[str, list[ToolCall]]:
        safe_parts: list[str] = []
        new_calls: list[ToolCall] = []
        while True:
            open_idx, open_kind = self._find_open()

            if open_idx < 0:
                partial = self._trailing_partial_open_length()
                if partial == 0:
                    safe_parts.append(self._buffer)
                    self._buffer = ""
                else:
                    safe_parts.append(self._buffer[:-partial])
                    self._buffer = self._buffer[-partial:]
                break

            close_idx, close_len = self._find_close(open_kind, open_idx)
            if close_idx < 0:
                # Open tag seen, close tag not yet: emit prefix, keep the rest.
                safe_parts.append(self._buffer[:open_idx])
                self._buffer = self._buffer[open_idx:]
                break

            end = close_idx + close_len
            safe_parts.append(self._buffer[:open_idx])
            tool_block = self._buffer[open_idx:end]
            _, parsed = self._adapter._extract_xml_tool_calls(
                tool_block, start_index=self._next_tool_index
            )
            self._next_tool_index += len(parsed)
            new_calls.extend(parsed)
            self._buffer = self._buffer[end:]
            continue

        return "".join(safe_parts), new_calls


def _partial_tag_suffix_length(text: str, tag: str) -> int:
    """Return the longest suffix of `text` that is also a strict prefix of `tag`."""
    max_check = min(len(text), len(tag) - 1)
    for size in range(max_check, 0, -1):
        if tag.startswith(text[-size:]):
            return size
    return 0


_BODY_RPM_RE = re.compile(r"(\d+)\s*requests?\s*per\s*minute", re.IGNORECASE)
_BODY_PER_DAY_RE = re.compile(
    r"(input\s+)?tokens?\s+per\s+day|requests?\s+per\s+day", re.IGNORECASE
)


def _parse_retry_after_from_body(body: str) -> float | None:
    """Best-effort parse of a 429 body for `N requests per minute`.

    Inspired by Simon Roux's AlbertCode (api.py): when Albert refuses with
    a textual error like `"Limit exceeded: 50 requests per minute"`,
    use that to compute a reasonable backoff (60/N + 0.1).
    """
    if not body:
        return None
    match = _BODY_RPM_RE.search(body[:500])
    if match is None:
        return None
    rpm = max(1, int(match.group(1)))
    return (60.0 / rpm) + 0.1


def is_terminal_rate_limit(body: str) -> bool:
    """Return True if the 429 body says the daily quota (rpd/tpd) is exhausted.

    Albert returns bodies like `"2460000 input tokens per day exceeded
    (remaining: 0)."` when the daily budget is gone. Sleeping and retrying
    that won't help until the day rolls over - we'd just burn the rpm on
    requests that all return 429 immediately.
    """
    if not body:
        return False
    return _BODY_PER_DAY_RE.search(body[:500]) is not None


def _parse_retry_after(value: str) -> float | None:
    """Parse a Retry-After header. Returns seconds, or None if unparsable.

    Per RFC 7231, the value may be either a non-negative integer (seconds)
    or an HTTP-date.
    """
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        target = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if target is None:
        return None
    if target.tzinfo is None:
        target = target.replace(tzinfo=dt.UTC)
    delta = (target - dt.datetime.now(dt.UTC)).total_seconds()
    return max(0.0, delta)


def _emit_through_xml_parser(
    chunk: LLMChunk, parser: XmlToolCallStreamParser
) -> Iterator[LLMChunk]:
    """Pipe a streamed chunk through the incremental XML parser.

    Yields cleaned content chunks and synthesized tool-call chunks, preserving
    the upstream usage so token counts still reach the agent loop.
    """
    delta_content = chunk.message.content or ""
    safe_content, new_tool_calls = parser.feed(str(delta_content))

    has_safe_content = bool(safe_content)
    has_tool_calls = bool(new_tool_calls)
    has_usage = chunk.usage is not None

    if not (has_safe_content or has_tool_calls or has_usage):
        return

    yield LLMChunk(
        message=LLMMessage(
            role=chunk.message.role,
            content=safe_content if has_safe_content else None,
            tool_calls=new_tool_calls if has_tool_calls else None,
            reasoning_content=chunk.message.reasoning_content,
            reasoning_signature=chunk.message.reasoning_signature,
        ),
        usage=chunk.usage,
    )


class GenericBackend:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        provider: ProviderConfig,
        timeout: float = 720.0,
    ) -> None:
        """Initialize the backend.

        Args:
            client: Optional httpx client to use. If not provided, one will be created.
        """
        self._client = client
        self._owns_client = client is None
        self._provider = provider
        self._timeout = timeout

    async def __aenter__(self) -> GenericBackend:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
            self._owns_client = True
        return self._client

    async def complete(
        self,
        *,
        model: ModelConfig,
        messages: Sequence[LLMMessage],
        temperature: float = 0.2,
        tools: list[AvailableTool] | None = None,
        max_tokens: int | None = None,
        tool_choice: StrToolChoice | AvailableTool | None = None,
        extra_headers: dict[str, str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> LLMChunk:
        api_key = (
            os.getenv(self._provider.api_key_env_var)
            if self._provider.api_key_env_var
            else None
        )

        api_style = getattr(self._provider, "api_style", "openai")
        adapter = ADAPTERS[api_style]

        req = adapter.prepare_request(
            model_name=model.name,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            enable_streaming=False,
            provider=self._provider,
            api_key=api_key,
            thinking=model.thinking,
        )

        headers = req.headers
        if extra_headers:
            headers.update(extra_headers)

        base = req.base_url or self._provider.api_base
        url = f"{base}{req.endpoint}"

        throttler = get_throttler(self._provider)
        await throttler.acquire(model_name=model.name)

        try:
            res_data, _ = await self._make_request(
                url, req.body, headers, model_alias=model.alias
            )
            chunk = adapter.parse_response(res_data, self._provider)
            if chunk.usage is not None:
                throttler.record_request(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                )
            else:
                throttler.record_request()
            throttler.record_success(model_alias=model.alias)
            return chunk

        except TerminalRateLimitError as e:
            raise BackendErrorBuilder.build_terminal_rate_limit(
                provider=self._provider.name,
                endpoint=url,
                terminal=e,
                model=model.name,
                messages=messages,
                temperature=temperature,
                has_tools=bool(tools),
                tool_choice=tool_choice,
            ) from e
        except httpx.HTTPStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=url,
                response=e.response,
                headers=e.response.headers,
                model=model.name,
                messages=messages,
                temperature=temperature,
                has_tools=bool(tools),
                tool_choice=tool_choice,
            ) from e
        except httpx.RequestError as e:
            raise BackendErrorBuilder.build_request_error(
                provider=self._provider.name,
                endpoint=url,
                error=e,
                model=model.name,
                messages=messages,
                temperature=temperature,
                has_tools=bool(tools),
                tool_choice=tool_choice,
            ) from e

    async def complete_streaming(
        self,
        *,
        model: ModelConfig,
        messages: Sequence[LLMMessage],
        temperature: float = 0.2,
        tools: list[AvailableTool] | None = None,
        max_tokens: int | None = None,
        tool_choice: StrToolChoice | AvailableTool | None = None,
        extra_headers: dict[str, str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> AsyncGenerator[LLMChunk, None]:
        # `force_non_streaming` is a fallback for providers that simply do not
        # support streaming. It downgrades to a single non-streaming call.
        if self._provider.force_non_streaming:
            result = await self.complete(
                model=model,
                messages=messages,
                temperature=temperature,
                tools=tools,
                max_tokens=max_tokens,
                tool_choice=tool_choice,
                extra_headers=extra_headers,
                metadata=metadata,
            )
            yield result
            return

        api_key = (
            os.getenv(self._provider.api_key_env_var)
            if self._provider.api_key_env_var
            else None
        )

        api_style = getattr(self._provider, "api_style", "openai")
        adapter = ADAPTERS[api_style]

        # Albert/vLLM emits Qwen tool calls as raw XML inside `delta.content`,
        # split across many tiny SSE chunks. We feed those deltas to an
        # incremental parser that reconstructs the tool calls and emits clean
        # text chunks in between. Activated per-provider.
        xml_parser: XmlToolCallStreamParser | None = None
        if self._provider.streaming_xml_tool_calls and isinstance(
            adapter, OpenAIAdapter
        ):
            xml_parser = XmlToolCallStreamParser(adapter)

        req = adapter.prepare_request(
            model_name=model.name,
            messages=messages,
            temperature=temperature,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            enable_streaming=True,
            provider=self._provider,
            api_key=api_key,
            thinking=model.thinking,
        )

        headers = req.headers
        if extra_headers:
            headers.update(extra_headers)

        base = req.base_url or self._provider.api_base
        url = f"{base}{req.endpoint}"

        throttler = get_throttler(self._provider)
        await throttler.acquire(model_name=model.name)

        last_usage = LLMUsage()

        try:
            async for res_data in self._make_streaming_request(
                url, req.body, headers, model_alias=model.alias
            ):
                chunk = adapter.parse_response(res_data, self._provider)
                if chunk.usage is not None:
                    last_usage = chunk.usage
                if xml_parser is None:
                    yield chunk
                    continue
                for transformed in _emit_through_xml_parser(chunk, xml_parser):
                    yield transformed

            if xml_parser is not None:
                leftover_content, leftover_calls = xml_parser.flush()
                if leftover_content or leftover_calls:
                    yield LLMChunk(
                        message=LLMMessage(
                            role=Role.assistant,
                            content=leftover_content or None,
                            tool_calls=leftover_calls or None,
                        ),
                        usage=None,
                    )

            throttler.record_request(
                prompt_tokens=last_usage.prompt_tokens,
                completion_tokens=last_usage.completion_tokens,
            )
            throttler.record_success(model_alias=model.alias)

        except TerminalRateLimitError as e:
            raise BackendErrorBuilder.build_terminal_rate_limit(
                provider=self._provider.name,
                endpoint=url,
                terminal=e,
                model=model.name,
                messages=messages,
                temperature=temperature,
                has_tools=bool(tools),
                tool_choice=tool_choice,
            ) from e
        except httpx.HTTPStatusError as e:
            raise BackendErrorBuilder.build_http_error(
                provider=self._provider.name,
                endpoint=url,
                response=e.response,
                headers=e.response.headers,
                model=model.name,
                messages=messages,
                temperature=temperature,
                has_tools=bool(tools),
                tool_choice=tool_choice,
            ) from e
        except httpx.RequestError as e:
            raise BackendErrorBuilder.build_request_error(
                provider=self._provider.name,
                endpoint=url,
                error=e,
                model=model.name,
                messages=messages,
                temperature=temperature,
                has_tools=bool(tools),
                tool_choice=tool_choice,
            ) from e

    class HTTPResponse(NamedTuple):
        data: dict[str, Any]
        headers: dict[str, str]

    @async_retry(tries=3)
    async def _make_request(
        self,
        url: str,
        data: bytes,
        headers: dict[str, str],
        model_alias: str | None = None,
    ) -> HTTPResponse:
        client = self._get_client()
        response = await client.post(url, content=data, headers=headers)
        await self._handle_429(response, model_alias=model_alias)
        response.raise_for_status()

        response_headers = dict(response.headers.items())
        response_body = response.json()
        return self.HTTPResponse(response_body, response_headers)

    async def _handle_429(
        self, response: httpx.Response, *, model_alias: str | None = None
    ) -> None:
        """If the upstream returned 429, log it, sleep Retry-After, then let
        async_retry retry. Also records the event on the throttler so it can
        adapt future calls.

        On a terminal 429 (daily quota exhausted - rpd/tpd), raises
        TerminalRateLimitError instead of sleeping: retrying won't help until
        the day rolls over, so we fail fast with the server message.
        """
        if response.status_code != HTTP_TOO_MANY_REQUESTS:
            return
        try:
            body_text = response.text
        except RuntimeError:
            body_text = ""
        logger.warning("429 body: %s", body_text[:300] if body_text else "(empty)")

        if is_terminal_rate_limit(body_text):
            get_throttler(self._provider).record_rate_limit(
                model_alias=model_alias
            )
            raise TerminalRateLimitError(
                status=HTTP_TOO_MANY_REQUESTS,
                headers=response.headers,
                body_text=body_text,
                reason="daily-quota",
            )

        retry_after = _parse_retry_after(response.headers.get("Retry-After", ""))
        if retry_after is None:
            retry_after = _parse_retry_after_from_body(body_text)
        throttler = get_throttler(self._provider)
        throttler.record_rate_limit(
            model_alias=model_alias, retry_after_seconds=retry_after
        )
        # If this 429 just armed the auto-fallback for this model, retrying
        # the same primary is wasteful: the next agent turn will switch to
        # the fallback model anyway. Raise a non-retryable error so the
        # agent loop sees it now instead of burning the remaining retries.
        if throttler.is_fallback_trigger_reached(model_alias):
            logger.warning(
                "Auto-fallback trigger reached for %s; aborting retries.",
                model_alias,
            )
            raise TerminalRateLimitError(
                status=HTTP_TOO_MANY_REQUESTS,
                headers=response.headers,
                body_text=body_text,
                reason="fallback-armed",
            )
        if retry_after is not None and retry_after > 0:
            logger.info(
                "Provider returned 429; sleeping %.2fs (Retry-After)", retry_after
            )
            await asyncio.sleep(retry_after)

    @async_generator_retry(tries=3)
    async def _make_streaming_request(
        self,
        url: str,
        data: bytes,
        headers: dict[str, str],
        model_alias: str | None = None,
    ) -> AsyncGenerator[dict[str, Any]]:
        client = self._get_client()
        async with client.stream(
            method="POST", url=url, content=data, headers=headers
        ) as response:
            if not response.is_success:
                await response.aread()
            await self._handle_429(response, model_alias=model_alias)
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip() == "":
                    continue

                DELIM_CHAR = ":"
                if f"{DELIM_CHAR} " not in line:
                    raise ValueError(
                        f"Stream chunk improperly formatted. "
                        f"Expected `key{DELIM_CHAR} value`, received `{line}`"
                    )
                delim_index = line.find(DELIM_CHAR)
                key = line[0:delim_index]
                value = line[delim_index + 2 :]

                if key != "data":
                    # This might be the case with openrouter, so we just ignore it
                    continue
                if value == "[DONE]":
                    return
                yield json.loads(value.strip())

    async def count_tokens(
        self,
        *,
        model: ModelConfig,
        messages: Sequence[LLMMessage],
        temperature: float = 0.0,
        tools: list[AvailableTool] | None = None,
        tool_choice: StrToolChoice | AvailableTool | None = None,
        extra_headers: dict[str, str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> int:
        probe_messages = list(messages)
        if not probe_messages or probe_messages[-1].role != Role.user:
            probe_messages.append(LLMMessage(role=Role.user, content=""))

        result = await self.complete(
            model=model,
            messages=probe_messages,
            temperature=temperature,
            tools=tools,
            max_tokens=16,  # Minimal amount for openrouter with openai models
            tool_choice=tool_choice,
            extra_headers=extra_headers,
        )
        if result.usage is None:
            raise ValueError("Missing usage in non streaming completion")

        return result.usage.prompt_tokens

    async def close(self) -> None:
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None
