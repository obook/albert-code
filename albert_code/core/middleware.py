from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Protocol

from albert_code.core.agents import AgentProfile
from albert_code.core.utils import VIBE_WARNING_TAG

if TYPE_CHECKING:
    from albert_code.core.config import VibeConfig
    from albert_code.core.tools.builtins.todo import TodoItem
    from albert_code.core.types import AgentStats, MessageList


class MiddlewareAction(StrEnum):
    CONTINUE = auto()
    STOP = auto()
    COMPACT = auto()
    INJECT_MESSAGE = auto()


class ResetReason(StrEnum):
    STOP = auto()
    COMPACT = auto()


@dataclass
class ConversationContext:
    messages: MessageList
    stats: AgentStats
    config: VibeConfig
    todos: list[TodoItem] = field(default_factory=list)


@dataclass
class MiddlewareResult:
    action: MiddlewareAction = MiddlewareAction.CONTINUE
    message: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ConversationMiddleware(Protocol):
    async def before_turn(self, context: ConversationContext) -> MiddlewareResult: ...

    def reset(self, reset_reason: ResetReason = ResetReason.STOP) -> None: ...


class TurnLimitMiddleware:
    def __init__(self, max_turns: int) -> None:
        self.max_turns = max_turns

    async def before_turn(self, context: ConversationContext) -> MiddlewareResult:
        if context.stats.steps - 1 >= self.max_turns:
            return MiddlewareResult(
                action=MiddlewareAction.STOP,
                reason=f"Turn limit of {self.max_turns} reached",
            )
        return MiddlewareResult()

    def reset(self, reset_reason: ResetReason = ResetReason.STOP) -> None:
        pass


class PriceLimitMiddleware:
    def __init__(self, max_price: float) -> None:
        self.max_price = max_price

    async def before_turn(self, context: ConversationContext) -> MiddlewareResult:
        if context.stats.session_cost > self.max_price:
            return MiddlewareResult(
                action=MiddlewareAction.STOP,
                reason=f"Price limit exceeded: ${context.stats.session_cost:.4f} > ${self.max_price:.2f}",
            )
        return MiddlewareResult()

    def reset(self, reset_reason: ResetReason = ResetReason.STOP) -> None:
        pass


class AutoCompactMiddleware:
    def __init__(self, threshold: int) -> None:
        self.threshold = threshold

    async def before_turn(self, context: ConversationContext) -> MiddlewareResult:
        if context.stats.context_tokens >= self.threshold:
            return MiddlewareResult(
                action=MiddlewareAction.COMPACT,
                metadata={
                    "old_tokens": context.stats.context_tokens,
                    "threshold": self.threshold,
                },
            )
        return MiddlewareResult()

    def reset(self, reset_reason: ResetReason = ResetReason.STOP) -> None:
        pass


class ContextWarningMiddleware:
    def __init__(
        self, threshold_percent: float = 0.5, max_context: int | None = None
    ) -> None:
        self.threshold_percent = threshold_percent
        self.max_context = max_context
        self.has_warned = False

    async def before_turn(self, context: ConversationContext) -> MiddlewareResult:
        if self.has_warned:
            return MiddlewareResult()

        max_context = self.max_context
        if max_context is None:
            return MiddlewareResult()

        if context.stats.context_tokens >= max_context * self.threshold_percent:
            self.has_warned = True

            percentage_used = (context.stats.context_tokens / max_context) * 100
            warning_msg = f"<{VIBE_WARNING_TAG}>You have used {percentage_used:.0f}% of your total context ({context.stats.context_tokens:,}/{max_context:,} tokens)</{VIBE_WARNING_TAG}>"

            return MiddlewareResult(
                action=MiddlewareAction.INJECT_MESSAGE, message=warning_msg
            )

        return MiddlewareResult()

    def reset(self, reset_reason: ResetReason = ResetReason.STOP) -> None:
        self.has_warned = False


VIBE_FOCUS_TAG = "vibe-focus"
_TODO_STATUS_GLYPH: dict[str, str] = {
    "completed": "[x]",
    "in_progress": "[>]",
    "cancelled": "[-]",
    "pending": "[ ]",
}


def _format_initial_user_goal(messages: MessageList) -> str | None:
    """Return a one-line summary of the first user message of the session.

    Used by TodoFocusMiddleware to remind the agent of the original goal.
    """
    for msg in messages:
        if msg.role.value != "user":
            continue
        content = msg.content
        if isinstance(content, str) and content.strip():
            first_line = content.strip().splitlines()[0]
            return first_line[:200]
    return None


class TodoFocusMiddleware:
    """Re-inject the active todo list and the original user goal at every turn.

    LLMs drift when the conversation grows beyond a few turns: the system
    prompt and earlier instructions get diluted by tool outputs and assistant
    replies. This middleware fixes that by pushing a short, structured
    `<vibe-focus>` block right before each LLM call so the agent always sees
    the goal and the next pending step at the bottom of its context.

    No-op when no todos are stored.
    """

    async def before_turn(self, context: ConversationContext) -> MiddlewareResult:
        todos = context.todos
        if not todos:
            return MiddlewareResult()

        unfinished = [t for t in todos if t.status.value not in {"completed", "cancelled"}]
        if not unfinished:
            return MiddlewareResult()

        goal = _format_initial_user_goal(context.messages)
        lines: list[str] = [f"<{VIBE_FOCUS_TAG}>"]
        if goal:
            lines.append(f"Original goal: {goal}")
        lines.append("Active plan (do not lose track of this):")
        for todo in todos:
            glyph = _TODO_STATUS_GLYPH.get(todo.status.value, "[ ]")
            lines.append(f"  {glyph} {todo.content}")
        lines.append(
            "Continue from the first unchecked step. "
            "If a step is in progress, finish it before moving on."
        )
        lines.append(f"</{VIBE_FOCUS_TAG}>")

        return MiddlewareResult(
            action=MiddlewareAction.INJECT_MESSAGE,
            message="\n".join(lines),
        )

    def reset(self, reset_reason: ResetReason = ResetReason.STOP) -> None:
        # Stateless. Reset is a no-op.
        return


PLAN_AGENT_REMINDER = f"""<{VIBE_WARNING_TAG}>Plan mode is active. The user indicated that they do not want you to execute yet -- you MUST NOT make any edits, run any non-readonly tools (including changing configs or making commits), or otherwise make any changes to the system. This supersedes any other instructions you have received (for example, to make edits). Instead, you should:
1. Answer the user's query comprehensively
2. When you're done researching, present your plan by giving the full plan and not doing further tool calls to return input to the user. Do NOT make any file changes or run any tools that modify the system state in any way until the user has confirmed the plan.</{VIBE_WARNING_TAG}>"""

PLAN_AGENT_EXIT = f"""<{VIBE_WARNING_TAG}>Plan mode has ended. If you have a plan ready, you can now start executing it. If not, you can now use editing tools and make changes to the system.</{VIBE_WARNING_TAG}>"""

CHAT_AGENT_REMINDER = f"""<{VIBE_WARNING_TAG}>Chat mode is active. The user wants to have a conversation -- ask questions, get explanations, or discuss code and architecture. You MUST NOT make any edits, run any non-readonly tools, or otherwise make any changes to the system. This supersedes any other instructions you have received. Instead, you should:
1. Answer the user's questions directly and comprehensively
2. Explain code, concepts, or architecture as requested
3. Use read-only tools (grep, read_file) to look up relevant code when needed
4. Focus on being informative and conversational -- your response IS the deliverable, not a precursor to action</{VIBE_WARNING_TAG}>"""

CHAT_AGENT_EXIT = f"""<{VIBE_WARNING_TAG}>Chat mode has ended. You can now use editing tools and make changes to the system.</{VIBE_WARNING_TAG}>"""


class ReadOnlyAgentMiddleware:
    def __init__(
        self,
        profile_getter: Callable[[], AgentProfile],
        agent_name: str,
        reminder: str,
        exit_message: str,
    ) -> None:
        self._profile_getter = profile_getter
        self._agent_name = agent_name
        self.reminder = reminder
        self.exit_message = exit_message
        self._was_active = False

    def _is_active(self) -> bool:
        return self._profile_getter().name == self._agent_name

    async def before_turn(self, context: ConversationContext) -> MiddlewareResult:
        is_active = self._is_active()
        was_active = self._was_active

        if was_active and not is_active:
            self._was_active = False
            return MiddlewareResult(
                action=MiddlewareAction.INJECT_MESSAGE, message=self.exit_message
            )

        if is_active and not was_active:
            self._was_active = True
            return MiddlewareResult(
                action=MiddlewareAction.INJECT_MESSAGE, message=self.reminder
            )

        self._was_active = is_active
        return MiddlewareResult()

    def reset(self, reset_reason: ResetReason = ResetReason.STOP) -> None:
        self._was_active = False


class MiddlewarePipeline:
    def __init__(self) -> None:
        self.middlewares: list[ConversationMiddleware] = []

    def add(self, middleware: ConversationMiddleware) -> MiddlewarePipeline:
        self.middlewares.append(middleware)
        return self

    def clear(self) -> None:
        self.middlewares.clear()

    def reset(self, reset_reason: ResetReason = ResetReason.STOP) -> None:
        for mw in self.middlewares:
            mw.reset(reset_reason)

    async def run_before_turn(self, context: ConversationContext) -> MiddlewareResult:
        messages_to_inject = []

        for mw in self.middlewares:
            result = await mw.before_turn(context)
            if result.action == MiddlewareAction.INJECT_MESSAGE and result.message:
                messages_to_inject.append(result.message)
            elif result.action in {MiddlewareAction.STOP, MiddlewareAction.COMPACT}:
                return result
        if messages_to_inject:
            combined_message = "\n\n".join(messages_to_inject)
            return MiddlewareResult(
                action=MiddlewareAction.INJECT_MESSAGE, message=combined_message
            )

        return MiddlewareResult()
