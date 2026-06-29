import functools
import time
from typing import Any, Callable

from flight_recorder.log_config import get_logger
from flight_recorder.models import Step, StepType, Trace

logger = get_logger(__name__)

_original_functions: dict[str, tuple[Any, str, Callable[..., Any]]] = {}

_auto_trace: Trace | None = None


def _get_or_create_auto_trace() -> Trace:
    global _auto_trace
    if _auto_trace is None:
        _auto_trace = Trace(agent_name="auto_record")
    return _auto_trace


def _add_step(
    step_type: StepType,
    name: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    duration_ms: float = 0.0,
) -> None:
    try:
        trace = _get_or_create_auto_trace()
        step = Step(
            index=len(trace.steps),
            step_type=step_type,
            name=name,
            input_data=input_data,
            output_data=output_data,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_ms=duration_ms,
        )
        trace.steps.append(step)
    except Exception as e:
        logger.debug("Failed to record step: %s", e)


def _wrap_openai() -> None:
    try:
        import openai

        if hasattr(openai, "ChatCompletion"):
            original_create = openai.ChatCompletion.create
            if not getattr(original_create, "_flight_recorder_wrapped", False):

                @functools.wraps(original_create)
                def wrapped_create(*args: Any, **kwargs: Any) -> Any:
                    model = kwargs.get("model", "unknown")
                    messages = kwargs.get("messages", [])
                    prompt = str(messages)[:500]

                    start = time.perf_counter()
                    result = original_create(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start) * 1000

                    try:
                        response_content = ""
                        if hasattr(result, "choices") and result.choices:
                            response_content = (
                                result.choices[0].message.content or ""
                            )

                        tokens_in = (
                            getattr(result.usage, "prompt_tokens", 0)
                            if hasattr(result, "usage")
                            else 0
                        )
                        tokens_out = (
                            getattr(result.usage, "completion_tokens", 0)
                            if hasattr(result, "usage")
                            else 0
                        )

                        _add_step(
                            StepType.LLM_CALL,
                            f"openai/{model}",
                            {"prompt": prompt},
                            {"response": response_content[:500]},
                            tokens_in=tokens_in,
                            tokens_out=tokens_out,
                            duration_ms=duration_ms,
                        )
                    except Exception as e:
                        logger.debug("Failed to record OpenAI call: %s", e)

                    return result

                wrapped_create._flight_recorder_wrapped = True  # type: ignore[attr-defined]
                openai.ChatCompletion.create = wrapped_create  # type: ignore[attr-defined]
                _original_functions["openai.ChatCompletion.create"] = (
                    openai,
                    "ChatCompletion.create",
                    original_create,
                )
                logger.info("Wrapped OpenAI ChatCompletion.create")

        if hasattr(openai, "OpenAI"):
            original_init = openai.OpenAI.__init__
            if not getattr(original_init, "_flight_recorder_wrapped", False):

                @functools.wraps(original_init)
                def wrapped_init(self: Any, *args: Any, **kwargs: Any) -> None:
                    original_init(self, *args, **kwargs)
                    if hasattr(self, "chat") and hasattr(
                        self.chat, "completions"
                    ):
                        original_chat_create = self.chat.completions.create

                        @functools.wraps(original_chat_create)
                        def wrapped_chat_create(
                            *chat_args: Any, **chat_kwargs: Any
                        ) -> Any:
                            model = chat_kwargs.get("model", "unknown")
                            messages = chat_kwargs.get("messages", [])
                            prompt = str(messages)[:500]

                            start = time.perf_counter()
                            result = original_chat_create(
                                *chat_args, **chat_kwargs
                            )
                            duration_ms = (
                                time.perf_counter() - start
                            ) * 1000

                            try:
                                response_content = ""
                                if hasattr(result, "choices") and result.choices:
                                    response_content = (
                                        result.choices[0].message.content or ""
                                    )

                                tokens_in = (
                                    getattr(result.usage, "prompt_tokens", 0)
                                    if hasattr(result, "usage")
                                    else 0
                                )
                                tokens_out = (
                                    getattr(
                                        result.usage, "completion_tokens", 0
                                    )
                                    if hasattr(result, "usage")
                                    else 0
                                )

                                _add_step(
                                    StepType.LLM_CALL,
                                    f"openai/{model}",
                                    {"prompt": prompt},
                                    {"response": response_content[:500]},
                                    tokens_in=tokens_in,
                                    tokens_out=tokens_out,
                                    duration_ms=duration_ms,
                                )
                            except Exception as e:
                                logger.debug(
                                    "Failed to record OpenAI call: %s", e
                                )

                            return result

                        self.chat.completions.create = wrapped_chat_create  # type: ignore[assignment]

                wrapped_init._flight_recorder_wrapped = True  # type: ignore[attr-defined]
                openai.OpenAI.__init__ = wrapped_init  # type: ignore[assignment]
                _original_functions["openai.OpenAI.__init__"] = (
                    openai,
                    "OpenAI.__init__",
                    original_init,
                )
                logger.info("Wrapped OpenAI client")
    except ImportError:
        logger.debug("OpenAI not installed, skipping")


def _wrap_anthropic() -> None:
    try:
        import anthropic

        if hasattr(anthropic, "Anthropic"):
            original_init = anthropic.Anthropic.__init__
            if not getattr(original_init, "_flight_recorder_wrapped", False):

                @functools.wraps(original_init)
                def wrapped_init(self: Any, *args: Any, **kwargs: Any) -> None:
                    original_init(self, *args, **kwargs)
                    if hasattr(self, "messages"):
                        original_create = self.messages.create

                        @functools.wraps(original_create)
                        def wrapped_create(
                            *create_args: Any, **create_kwargs: Any
                        ) -> Any:
                            model = create_kwargs.get("model", "unknown")
                            messages = create_kwargs.get("messages", [])
                            prompt = str(messages)[:500]

                            start = time.perf_counter()
                            result = original_create(
                                *create_args, **create_kwargs
                            )
                            duration_ms = (
                                time.perf_counter() - start
                            ) * 1000

                            try:
                                response_content = ""
                                if hasattr(result, "content") and result.content:
                                    response_content = (
                                        result.content[0].text
                                        if result.content
                                        else ""
                                    )

                                tokens_in = (
                                    getattr(result.usage, "input_tokens", 0)
                                    if hasattr(result, "usage")
                                    else 0
                                )
                                tokens_out = (
                                    getattr(result.usage, "output_tokens", 0)
                                    if hasattr(result, "usage")
                                    else 0
                                )

                                _add_step(
                                    StepType.LLM_CALL,
                                    f"anthropic/{model}",
                                    {"prompt": prompt},
                                    {"response": response_content[:500]},
                                    tokens_in=tokens_in,
                                    tokens_out=tokens_out,
                                    duration_ms=duration_ms,
                                )
                            except Exception as e:
                                logger.debug(
                                    "Failed to record Anthropic call: %s", e
                                )

                            return result

                        self.messages.create = wrapped_create  # type: ignore[assignment]

                wrapped_init._flight_recorder_wrapped = True  # type: ignore[attr-defined]
                anthropic.Anthropic.__init__ = wrapped_init  # type: ignore[assignment]
                _original_functions["anthropic.Anthropic.__init__"] = (
                    anthropic,
                    "Anthropic.__init__",
                    original_init,
                )
                logger.info("Wrapped Anthropic client")
    except ImportError:
        logger.debug("Anthropic not installed, skipping")


def _wrap_langchain() -> None:
    try:
        from langchain.callbacks.base import BaseCallbackHandler
        from langchain.schema import LLMResult

        class FlightRecorderCallback(BaseCallbackHandler):
            def on_llm_start(
                self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
            ) -> None:
                self._llm_start_time = time.perf_counter()
                self._llm_prompts = prompts

            def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
                duration_ms = 0.0
                if hasattr(self, "_llm_start_time"):
                    duration_ms = (
                        time.perf_counter() - self._llm_start_time
                    ) * 1000

                for generation_list in response.generations:
                    for gen in generation_list:
                        _add_step(
                            StepType.LLM_CALL,
                            "langchain/llm",
                            {"prompt": str(getattr(self, "_llm_prompts", ""))},
                            {"response": gen.text[:500]},
                            duration_ms=duration_ms,
                        )

            def on_tool_start(
                self,
                serialized: dict[str, Any],
                input_str: str,
                **kwargs: Any,
            ) -> None:
                self._tool_start_time = time.perf_counter()
                self._tool_name = serialized.get("name", "unknown")
                self._tool_input = input_str

            def on_tool_end(self, output: str, **kwargs: Any) -> None:
                duration_ms = 0.0
                if hasattr(self, "_tool_start_time"):
                    duration_ms = (
                        time.perf_counter() - self._tool_start_time
                    ) * 1000

                _add_step(
                    StepType.TOOL_CALL,
                    getattr(self, "_tool_name", "unknown"),
                    {"input": getattr(self, "_tool_input", "")},
                    {"output": output[:500]},
                    duration_ms=duration_ms,
                )

        _original_functions["langchain_callback"] = (
            None,
            "FlightRecorderCallback",
            FlightRecorderCallback,
        )
        logger.info("Created LangChain callback handler")
    except ImportError:
        logger.debug("LangChain not installed, skipping")


def get_auto_trace() -> Trace | None:
    return _auto_trace


def clear_auto_trace() -> None:
    global _auto_trace
    _auto_trace = None


def auto_record(
    enable_openai: bool = True,
    enable_anthropic: bool = True,
    enable_langchain: bool = True,
) -> None:
    """Enable auto-injection for supported AI frameworks.

    Call this once at the start of your application to automatically record
    all AI framework calls without using @record decorator.

    Example::

        from flight_recorder import auto_record

        auto_record()  # That's it! All calls will be recorded

    """
    logger.info("Enabling auto-injection...")

    if enable_openai:
        _wrap_openai()
    if enable_anthropic:
        _wrap_anthropic()
    if enable_langchain:
        _wrap_langchain()

    logger.info("Auto-injection enabled")


def disable_auto_record() -> None:
    """Disable auto-injection and restore original functions."""
    logger.info("Disabling auto-injection...")

    for key, (module, attr_path, original) in list(_original_functions.items()):
        if module is None:
            continue

        parts = attr_path.split(".")
        obj: Any = module
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], original)
        logger.info("Restored %s", key)

    _original_functions.clear()
    logger.info("Auto-injection disabled")
