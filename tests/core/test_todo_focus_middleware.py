from __future__ import annotations

import pytest

from albert_code.core.middleware import (
    ConversationContext,
    MiddlewareAction,
    TodoFocusMiddleware,
)
from albert_code.core.tools.builtins.todo import TodoItem, TodoPriority, TodoStatus
from albert_code.core.types import AgentStats, LLMMessage, MessageList, Role
from tests.conftest import build_test_vibe_config


def _ctx(messages: list[LLMMessage], todos: list[TodoItem]) -> ConversationContext:
    return ConversationContext(
        messages=MessageList(initial=messages),
        stats=AgentStats(),
        config=build_test_vibe_config(),
        todos=todos,
    )


def _todo(
    content: str, status: TodoStatus = TodoStatus.PENDING, todo_id: str = "1"
) -> TodoItem:
    return TodoItem(
        id=todo_id, content=content, status=status, priority=TodoPriority.MEDIUM
    )


@pytest.mark.asyncio
class TestTodoFocusMiddleware:
    async def test_no_op_when_no_todos(self) -> None:
        mw = TodoFocusMiddleware()
        result = await mw.before_turn(_ctx([], []))
        assert result.action == MiddlewareAction.CONTINUE
        assert result.message is None

    async def test_no_op_when_all_todos_completed(self) -> None:
        mw = TodoFocusMiddleware()
        todos = [
            _todo("first", TodoStatus.COMPLETED, "1"),
            _todo("second", TodoStatus.CANCELLED, "2"),
        ]
        result = await mw.before_turn(_ctx([], todos))
        assert result.action == MiddlewareAction.CONTINUE

    async def test_injects_block_with_pending_todo(self) -> None:
        mw = TodoFocusMiddleware()
        todos = [_todo("Read README", TodoStatus.PENDING)]
        result = await mw.before_turn(_ctx([], todos))
        assert result.action == MiddlewareAction.INJECT_MESSAGE
        assert result.message is not None
        assert "<vibe-focus>" in result.message
        assert "</vibe-focus>" in result.message
        assert "Read README" in result.message
        assert "[ ]" in result.message  # pending glyph

    async def test_marks_status_glyphs(self) -> None:
        mw = TodoFocusMiddleware()
        todos = [
            _todo("done", TodoStatus.COMPLETED, "1"),
            _todo("active", TodoStatus.IN_PROGRESS, "2"),
            _todo("todo", TodoStatus.PENDING, "3"),
        ]
        result = await mw.before_turn(_ctx([], todos))
        assert result.message is not None
        assert "[x] done" in result.message
        assert "[>] active" in result.message
        assert "[ ] todo" in result.message

    async def test_includes_user_goal_when_first_user_message_present(self) -> None:
        mw = TodoFocusMiddleware()
        messages = [
            LLMMessage(role=Role.system, content="ignored"),
            LLMMessage(role=Role.user, content="Refactor the parser"),
        ]
        todos = [_todo("step", TodoStatus.PENDING)]
        result = await mw.before_turn(_ctx(messages, todos))
        assert result.message is not None
        assert "Original goal: Refactor the parser" in result.message

    async def test_long_user_goal_is_truncated(self) -> None:
        mw = TodoFocusMiddleware()
        long_goal = "x" * 500
        messages = [LLMMessage(role=Role.user, content=long_goal)]
        todos = [_todo("step", TodoStatus.PENDING)]
        result = await mw.before_turn(_ctx(messages, todos))
        assert result.message is not None
        # 200 char cap from _format_initial_user_goal
        assert "x" * 201 not in result.message

    async def test_only_keeps_first_line_of_goal(self) -> None:
        mw = TodoFocusMiddleware()
        messages = [
            LLMMessage(
                role=Role.user, content="Goal line\nDetail line that should be ignored"
            )
        ]
        todos = [_todo("step", TodoStatus.PENDING)]
        result = await mw.before_turn(_ctx(messages, todos))
        assert result.message is not None
        assert "Goal line" in result.message
        assert "Detail line" not in result.message
