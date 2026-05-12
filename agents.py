from __future__ import annotations

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover
    ChatGoogleGenerativeAI = None

try:
    from langgraph.prebuilt import create_react_agent
except ImportError:  # pragma: no cover
    create_react_agent = None

try:
    from config import get_gemini_api_key, get_gemini_model
    from tools import conceptual_tool, logical_tool, physical_tool  #added by swamy
except ImportError:  # pragma: no cover
    from .config import get_gemini_api_key, get_gemini_model
    from .tools import conceptual_tool, logical_tool, physical_tool  #added by swamy


_modeling_agent = None
_modeling_agent_error: Exception | None = None

tools = [conceptual_tool, logical_tool, physical_tool]  #added by swamy

system_prompt = """
You are a banking domain expert and enterprise data modeling agent.

Your job is to understand the user's intent and generate the appropriate data model.

-----------------------------------
INTENT DETECTION
-----------------------------------
Analyze the user query first and determine the required level:

1. CONCEPTUAL MODEL:
- User describes business entities and relationships
- No mention of tables, keys, schema
- Example: "customer has multiple accounts"

→ Call conceptual_tool ONLY and STOP

-----------------------------------

2. LOGICAL MODEL:
- User asks for tables, schema, normalization, keys
- Example: "design tables", "define schema"

→ First call conceptual_tool
→ Then call logical_tool
→ STOP

-----------------------------------

3. PHYSICAL MODEL:
- User asks for SQL, DDL, implementation
- Example: "create SQL tables", "generate DDL"

→ conceptual_tool → logical_tool → physical_tool
→ STOP

-----------------------------------

WORKFLOW RULES:
-----------------------------------
- ALWAYS use tools (never generate manually)
- NEVER skip conceptual step
- PASS full JSON between tools
- DO NOT modify tool outputs
- DO NOT summarize JSON


-----------------------------------
-----------------------------------
STRICT EXECUTION CONSTRAINTS
-----------------------------------

- Each tool MUST be called at most once per request.

- DO NOT call the same tool multiple times.

- DO NOT retry a tool even if the output seems incomplete.

- DO NOT go back to a previous step.
  (Example: Do NOT call conceptual_tool again after logical_tool)

- Follow a strictly linear flow:
  conceptual → logical → physical

- Once the required stage is completed, STOP immediately.

- Do NOT re-evaluate or refine previous outputs.

-----------------------------------

STOP CONDITIONS:
-----------------------------------
- If conceptual → STOP after conceptual_tool
- If logical → then execule conceptual tool and STOP after logical_tool
- If physical → Use conceptual and logical tool and STOP after physical_tool

-----------------------------------

OUTPUT FORMAT:
-----------------------------------
Return ONLY tool outputs (structured JSON)
Do NOT generate explanations unless asked
"""


def get_modeling_agent():
    global _modeling_agent, _modeling_agent_error
    if _modeling_agent is not None:
        return _modeling_agent
    if _modeling_agent_error is not None:
        raise RuntimeError(str(_modeling_agent_error)) from _modeling_agent_error

    gemini_api_key = get_gemini_api_key()
    if not gemini_api_key:
        _modeling_agent_error = RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY must be set to use Gemini.")
        raise _modeling_agent_error
    if ChatGoogleGenerativeAI is None:
        _modeling_agent_error = RuntimeError("langchain_google_genai is not installed.")
        raise _modeling_agent_error
    if create_react_agent is None:
        _modeling_agent_error = RuntimeError("langgraph is not installed.")
        raise _modeling_agent_error

    gemini_kwargs = {
        "model": get_gemini_model(),
        "temperature": 1,
        "max_retries": 0,
        "timeout": 30,
        "google_api_key": gemini_api_key,
    }
    llm = ChatGoogleGenerativeAI(**gemini_kwargs)
    _modeling_agent = create_react_agent(
        llm,
        tools,
        prompt=system_prompt,
    )
    return _modeling_agent


try:
    modeling_agent = get_modeling_agent()
except Exception:  # pragma: no cover
    modeling_agent = None
