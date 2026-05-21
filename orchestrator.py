from __future__ import annotations
import logging
logger = logging.getLogger(__name__)

import json
from dataclasses import dataclass
from typing import Any, Dict

_orchestrator_runtime_error: Exception | None = None
try:
    from agents import get_modeling_agent
    from tools import extract_json_from_tool_output
except ImportError:
    try:  # pragma: no cover
        from .agents import get_modeling_agent
        from .tools import extract_json_from_tool_output
    except ImportError as exc:  # pragma: no cover
        get_modeling_agent = None
        extract_json_from_tool_output = None
        _orchestrator_runtime_error = exc



def _message_content_as_text(content: Any) -> str:
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        content = "\n".join(text_parts)
    if not isinstance(content, str):
        content = str(content)
    return content


def _safe_extract_tool_json(tool_name: str, content: str) -> Dict[str, Any] | None:
    try:
        return extract_json_from_tool_output(content)
    except Exception as exc:
        logger.warning("Skipping non-JSON output from %s: %s", tool_name, exc)
        return None


@dataclass
class DataModelingOrchestrator:
    name: str = "data_modeling_orchestrator"

    def run(self, user_query: str) -> Dict[str, Any]:
        if _orchestrator_runtime_error is not None or get_modeling_agent is None:
            raise RuntimeError(
                "Modeling orchestrator runtime is not available. "
                f"Import error: {_orchestrator_runtime_error}"
            )

        modeling_agent = get_modeling_agent()
        result = modeling_agent.invoke(
            {"messages": [("user", user_query)]}
        )
         
        logger.info("Agent finished execution")


        conceptual_output = None
        logical_output = None
        physical_output = None
        final_text = ""

        for message in result.get("messages", []):
            name = getattr(message, "name", "") or ""
            content = _message_content_as_text(getattr(message, "content", ""))

            if name == "conceptual_tool":
                parsed_output = _safe_extract_tool_json(name, content)
                if parsed_output is not None:
                    conceptual_output = parsed_output
            elif name == "logical_tool":
                parsed_output = _safe_extract_tool_json(name, content)
                if parsed_output is not None:
                    logical_output = parsed_output
            elif name == "physical_tool":
                parsed_output = _safe_extract_tool_json(name, content)
                if parsed_output is not None:
                    physical_output = parsed_output

            if content:
                final_text = content

        return {
            "requirement": user_query,
            "conceptual_output": conceptual_output,
            "logical_output": logical_output,
            "physical_output": physical_output,
            "agent_final_answer": final_text,
        }
