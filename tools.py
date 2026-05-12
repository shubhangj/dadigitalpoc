from __future__ import annotations

import json
import re
from typing import Any, Dict, List

try:
    from langchain_core.tools import tool
except ImportError:  # pragma: no cover
    def tool(*decorator_args, **decorator_kwargs):
        if decorator_args and callable(decorator_args[0]) and len(decorator_args) == 1 and not decorator_kwargs:
            return decorator_args[0]

        def _decorator(func):
            return func

        return _decorator

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover
    ChatGoogleGenerativeAI = None

try:
    from config import get_gemini_api_key, get_gemini_model
    from core_banking_glossary_knowledge_base import CORE_BANKING_GLOSSARY_KNOWLEDGE_BASE
    from prompts import (
        get_conceptual_prompt,
        get_conceptual_update_prompt,
        get_logical_prompt,
    )
    from schemas import ConceptualModel, ConceptualUpdatePatch, LogicalModel
except ImportError:  # pragma: no cover
    from .config import get_gemini_api_key, get_gemini_model
    from .core_banking_glossary_knowledge_base import CORE_BANKING_GLOSSARY_KNOWLEDGE_BASE
    from .prompts import (
        get_conceptual_prompt,
        get_conceptual_update_prompt,
        get_logical_prompt,
    )
    from .schemas import ConceptualModel, ConceptualUpdatePatch, LogicalModel


def _client():
    api_key = get_gemini_api_key()
    if not api_key or ChatGoogleGenerativeAI is None:
        raise RuntimeError("Gemini client is not configured.")

    return ChatGoogleGenerativeAI(
        model=get_gemini_model(),
        google_api_key=api_key,
        temperature=1,
        max_retries=0,
        timeout=30,
    )


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def extract_json_from_tool_output(text: str) -> Dict[str, Any]:
    return _extract_json(text)


def _ask_json(prompt: str, system_message: str) -> Dict[str, Any]:
    response = _client().invoke([("system", system_message), ("human", prompt)])
    return _extract_json(response.content)


def _ask_structured_json(prompt: str, system_message: str, schema: Any) -> Dict[str, Any]:
    response = _client().with_structured_output(schema).invoke(
        [("system", system_message), ("human", prompt)]
    )
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if isinstance(response, dict):
        return response
    raise TypeError(f"Unsupported structured response: {type(response).__name__}")


def core_banking_glossary_context() -> str:
    return "\n".join(CORE_BANKING_GLOSSARY_KNOWLEDGE_BASE)


def _name_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _table_name(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip())
    name = re.sub(r"_+", "_", name).strip("_").upper()
    name = re.sub(r"^(DIM|FACT|FCT)_+", "", name)
    name = re.sub(r"_(DIM|FACT|FCT)$", "", name)
    return name


def _table_map(tables: List[Dict[str, Any]]) -> Dict[str, str]:
    return {
        table["table_name"]: _table_name(table["table_name"])
        for table in tables
        if table.get("table_name")
    }


def _id_columns(table: Dict[str, Any]) -> set[str]:
    foreign_keys = table.get("foreign_keys", [])
    return set(table.get("primary_key", [])) | {
        foreign_key.get("column", "") for foreign_key in foreign_keys
    }


def ensure_connected_conceptual_model(
    conceptual_output: Dict[str, Any],
    context: str = "",
) -> Dict[str, Any]:
    entities = conceptual_output.get("entities", [])
    relationships = [dict(item) for item in conceptual_output.get("relationships", [])]
    entity_names = [item.get("name", "") for item in entities if item.get("name")]

    if len(entity_names) <= 1:
        return {**conceptual_output, "relationships": relationships}

    connected = {
        _name_key(name)
        for relationship in relationships
        for name in [relationship.get("from_entity", ""), relationship.get("to_entity", "")]
        if name
    }
    anchor = next((name for name in entity_names if _name_key(name) in connected), entity_names[0])

    for entity_name in entity_names:
        if entity_name == anchor or _name_key(entity_name) in connected:
            continue
        relationships.append(
            {
                "from_entity": anchor,
                "to_entity": entity_name,
                "cardinality": "M:N",
                "description": f"{anchor} is associated with {entity_name} in the conceptual business model.",
                "label": "relates to",
            }
        )

    return {**conceptual_output, "relationships": relationships}


def _clean_logical(logical_output: Dict[str, Any]) -> Dict[str, Any]:
    tables = logical_output.get("tables", [])
    names = _table_map(tables)
    cleaned_tables = []

    for table in tables:
        table = dict(table)
        ids = _id_columns(table)
        table["table_name"] = names.get(table.get("table_name", ""), table.get("table_name", ""))
        table["columns"] = [
            {
                **column,
                "type": "number" if column.get("name") in ids else column.get("type"),
                "nullable": False if column.get("name") in ids else column.get("nullable", True),
            }
            for column in table.get("columns", [])
        ]
        table["foreign_keys"] = [
            {
                **foreign_key,
                "references_table": names.get(
                    foreign_key.get("references_table", ""),
                    _table_name(foreign_key.get("references_table", "")),
                ),
            }
            for foreign_key in table.get("foreign_keys", [])
        ]
        cleaned_tables.append(table)

    return {**logical_output, "tables": cleaned_tables}


def _physical_type(logical_type: str, is_id: bool) -> str:
    text = (logical_type or "").lower()
    if is_id:
        return "BIGINT"
    if any(item in text for item in ["decimal", "numeric", "amount", "money"]):
        return "DECIMAL(18,2)"
    if "date" in text and "time" in text:
        return "TIMESTAMP"
    if "date" in text:
        return "DATE"
    if "bool" in text:
        return "BOOLEAN"
    if "int" in text or "number" in text:
        return "INTEGER"
    if "text" in text:
        return "TEXT"
    return "VARCHAR(255)"


def _ddl(table: Dict[str, Any]) -> str:
    lines = []
    for column in table.get("columns", []):
        null_text = "NULL" if column.get("nullable", True) else "NOT NULL"
        lines.append(f"  {column['name']} {column['column_data_type']} {null_text}")

    if table.get("primary_key"):
        lines.append(
            f"  CONSTRAINT pk_{table['table_name']} PRIMARY KEY ({', '.join(table['primary_key'])})"
        )

    for foreign_key in table.get("foreign_keys", []):
        lines.append(
            f"  CONSTRAINT fk_{table['table_name']}_{foreign_key['column']} "
            f"FOREIGN KEY ({foreign_key['column']}) "
            f"REFERENCES {foreign_key['references_table']} ({foreign_key['references_column']})"
        )

    return f"CREATE TABLE {table['table_name']} (\n" + ",\n".join(lines) + "\n);"


def _physical_from_logical(logical_output: Dict[str, Any]) -> Dict[str, Any]:
    logical_output = _clean_logical(logical_output)
    tables = []
    indexes = []

    for logical_table in logical_output.get("tables", []):
        ids = _id_columns(logical_table)
        table_name = _table_name(logical_table.get("table_name", ""))
        columns = [
            {
                "name": column.get("name", ""),
                "column_data_type": _physical_type(column.get("type", ""), column.get("name") in ids),
                "nullable": False if column.get("name") in ids else column.get("nullable", True),
            }
            for column in logical_table.get("columns", [])
        ]
        foreign_keys = [
            {
                **foreign_key,
                "references_table": _table_name(foreign_key.get("references_table", "")),
            }
            for foreign_key in logical_table.get("foreign_keys", [])
        ]
        table_indexes = [
            {
                "index_name": f"IDX_{table_name}_{foreign_key['column'].upper()}",
                "table_name": table_name,
                "columns": [foreign_key["column"]],
                "unique": False,
            }
            for foreign_key in foreign_keys
        ]

        table = {
            "table_name": table_name,
            "columns": columns,
            "primary_key": logical_table.get("primary_key", []),
            "foreign_keys": foreign_keys,
            "indexes": table_indexes,
        }
        tables.append(table)
        indexes.extend(table_indexes)

    return {
        "tables": tables,
        "indexes": indexes,
        "ddl": [_ddl(table) for table in tables]
        + [
            f"CREATE INDEX {index['index_name']} ON {index['table_name']} ({', '.join(index['columns'])});"
            for index in indexes
        ],
    }


def conceptual_model_core(requirement: str) -> Dict[str, Any]:
    context = core_banking_glossary_context()
    prompt = get_conceptual_prompt(requirement, context)
    output = _ask_json(
        prompt,
        "You are a senior enterprise data architect. Use only the supplied core banking glossary.",
    )
    conceptual = ConceptualModel.model_validate(output)
    if not conceptual.requirement:
        conceptual.requirement = requirement
    if not conceptual.rag_context_used:
        conceptual.rag_context_used = context
    return ensure_connected_conceptual_model(conceptual.model_dump())


def conceptual_update_patch_core(
    conceptual_payload: Dict[str, Any],
    instruction: str,
) -> Dict[str, Any]:
    prompt = get_conceptual_update_prompt(conceptual_payload, instruction)
    output = _ask_structured_json(
        prompt,
        "Return a minimal conceptual model JSON patch for the user's update request.",
        ConceptualUpdatePatch,
    )
    return ConceptualUpdatePatch.model_validate(output).model_dump()


def logical_model_core(conceptual_payload: Dict[str, Any]) -> Dict[str, Any]:
    output = _ask_json(
        get_logical_prompt(conceptual_payload),
        "You are a senior data modeler creating a logical data model.",
    )
    return _clean_logical(LogicalModel.model_validate(output).model_dump())


def physical_model_core(logical_payload: Dict[str, Any]) -> Dict[str, Any]:
    return _physical_from_logical(logical_payload)


@tool
def conceptual_tool(requirement: str) -> str:
    """Generate conceptual model JSON from a business requirement."""
    return f"CONCEPTUAL_MODEL_JSON:\n{json.dumps(conceptual_model_core(requirement), indent=2)}"


@tool
def logical_tool(conceptual_json: str) -> str:
    """Generate logical model JSON from conceptual model JSON."""
    conceptual_payload = extract_json_from_tool_output(conceptual_json)
    return f"LOGICAL_MODEL_JSON:\n{json.dumps(logical_model_core(conceptual_payload), indent=2)}"


@tool
def physical_tool(logical_json: str) -> str:
    """Generate physical model JSON and DDL from logical model JSON."""
    logical_payload = extract_json_from_tool_output(logical_json)
    return f"PHYSICAL_MODEL_JSON:\n{json.dumps(physical_model_core(logical_payload), indent=2)}"
