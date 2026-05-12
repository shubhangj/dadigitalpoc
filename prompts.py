import json
from typing import Any, Dict


#editd by mani
def _compact_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"))


#editd by mani
def _logical_prompt_payload(conceptual_output: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": conceptual_output.get("title", ""),
        "scope": conceptual_output.get("scope", ""),
        "entities": [
            {
                "name": entity.get("name", ""),
                "description": entity.get("description", ""),
                "attributes": entity.get("attributes", []),
            }
            for entity in conceptual_output.get("entities", [])
        ],
        "relationships": [
            {
                "from_entity": relationship.get("from_entity", ""),
                "to_entity": relationship.get("to_entity", ""),
                "cardinality": relationship.get("cardinality", ""),
                "description": relationship.get("description", ""),
                "label": relationship.get("label"),
            }
            for relationship in conceptual_output.get("relationships", [])
        ],
        "business_rules": conceptual_output.get("business_rules", []),
    }


#editd by mani
def _physical_prompt_payload(logical_output: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tables": [
            {
                "table_name": table.get("table_name", ""),
                "source_entity": table.get("source_entity", ""),
                "columns": [
                    {
                        "name": column.get("name", ""),
                        "type": column.get("type", ""),
                        "nullable": column.get("nullable", True),
                    }
                    for column in table.get("columns", [])
                ],
                "primary_key": table.get("primary_key", []),
                "foreign_keys": table.get("foreign_keys", []),
            }
            for table in logical_output.get("tables", [])
        ]
    }


#editd by mani
def _conceptual_update_prompt_payload(conceptual_output: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": conceptual_output.get("title", ""),
        "entities": [
            {
                "name": entity.get("name", ""),
                "description": entity.get("description", ""),
            }
            for entity in conceptual_output.get("entities", [])
        ],
        "relationships": [
            {
                "from_entity": relationship.get("from_entity", ""),
                "to_entity": relationship.get("to_entity", ""),
                "cardinality": relationship.get("cardinality", ""),
                "label": relationship.get("label"),
            }
            for relationship in conceptual_output.get("relationships", [])
        ],
    }


def get_conceptual_prompt(requirement: str, context: str) -> str:
    return f"""
You are a banking domain expert and enterprise data architect.

Business requirement:
{requirement}

Authoritative glossary context:
{context}

Return ONLY valid JSON for a conceptual model.

Rules:
- Use the glossary context as the source of truth.
- Include only glossary-supported entities and relationships.
- Stay strictly conceptual: no PK, FK, SQL, indexing, storage, or calculations.
- Keep names business-friendly and prefer domain-specific names like Loan_Default over Default.
- Use entity profiles and column hints only to understand business meaning, not to design technical schemas.
- Every conceptual entity must participate in at least one relationship. Do not return isolated or orphan entities.

Required output:
{{
  "title": "string",
  "scope": "string",
  "entities": [
    {{
      "name": "string",
      "description": "string",
      "attributes": ["optional conceptual attributes"]
    }}
  ],
  "relationships": [
    {{
      "from_entity": "string",
      "to_entity": "string",
      "cardinality": "1:1 | 1:N | M:N",
      "description": "string",
      "label": "string"
    }}
  ],
  "business_rules": ["string"],
  "conceptual_summary": "string",
  "diagram_description": "string"
}}
""".strip()


#editd by mani
def get_conceptual_update_prompt(conceptual_output: Dict[str, Any], instruction: str) -> str:
    conceptual_json = _compact_json(_conceptual_update_prompt_payload(conceptual_output))

    return f"""
You are updating an existing conceptual ER model based on a user chat instruction.

Current conceptual model:
{conceptual_json}

User update instruction:
{instruction}

Return ONLY valid JSON describing the required patch.

Rules:
- Keep the existing conceptual structure unchanged unless the instruction requests a change.
- Reuse existing entity names exactly when referring to existing entities.
- Add a new entity only when the instruction clearly asks for one.
- Add or update only the relationships needed for the instruction.
- Stay strictly conceptual: no PK, FK, SQL, or physical details.
- If a new entity is added, also include at least one relationship that connects it to an existing or newly added entity.
- Use empty arrays when no entity or relationship is required; do not return placeholder values like "string".

Required output:
{{
  "entities_to_add": [
    {{
      "name": "string",
      "description": "string",
      "attributes": []
    }}
  ],
  "relationships_to_add_or_update": [
    {{
      "from_entity": "string",
      "to_entity": "string",
      "cardinality": "1:1 | 1:N | M:N",
      "description": "string",
      "label": "string"
    }}
  ]
}}
""".strip()


def get_logical_prompt(conceptual_output: Dict[str, Any]) -> str:
    conceptual_json = _compact_json(_logical_prompt_payload(conceptual_output))

    return f"""
You are a banking domain expert and enterprise data architect.

Approved conceptual model:
{conceptual_json}

Return ONLY valid JSON for a logical model.

Rules:
- Use ONLY the provided conceptual model.
- Stay at the logical level: no physical DDL, storage, indexing, or performance tuning.
- Convert entities into tables and preserve all conceptual relationships.
- Add business-relevant columns, primary keys, and foreign keys.
- Resolve every M:N relationship with an associative table.
- Use generic types only: string, number, date, datetime, boolean.
- Keep naming consistent, especially PK/FK pairs.
- All surrogate primary key and foreign key identifier columns must use type "number", not "string".
- Identifier columns such as Customer_ID, Facility_ID, Loan_ID, and bridge-table key columns must remain numeric.

Required output:
{{
  "source_entities": ["string"],
  "tables": [
    {{
      "table_name": "string",
      "source_entity": "string",
      "columns": [
        {{
          "name": "string",
          "type": "string",
          "nullable": false
        }}
      ],
      "primary_key": ["string"],
      "foreign_keys": [
        {{
          "column": "string",
          "references_table": "string",
          "references_column": "string"
        }}
      ]
    }}
  ],
  "relationships": [
    {{
      "from_entity": "string",
      "to_entity": "string",
      "cardinality": "string",
      "description": "string"
    }}
  ],
  "normalization_notes": ["string"]
}}
""".strip()


#added by swamy
def get_physical_prompt(logical_output: Dict[str, Any]) -> str:
    logical_json = _compact_json(_physical_prompt_payload(logical_output))
    return f"""
You are a banking domain expert and senior physical data modeling agent.

Approved logical model:
{logical_json}

Return ONLY valid JSON for a physical model.

Rules:
- Use ONLY the provided logical model.
- Do NOT invent, remove, or rename approved tables or relationships.
- Do NOT add database connection, execution, or engine-specific behavior.
- Map generic logical types to generic physical types.
- Preserve PK/FK constraints and add indexes mainly for foreign keys and joins.
- Generate generic DDL suitable for review/demo use.
- Use integer-style physical types for surrogate PK/FK identifier columns, for example BIGINT.
- Do NOT use VARCHAR/TEXT for surrogate primary key or foreign key columns.

Required output:
{{
  "tables": [
    {{
      "table_name": "string",
      "columns": [
        {{
          "name": "string",
          "column_data_type": "string",
          "nullable": false
        }}
      ],
      "primary_key": ["string"],
      "foreign_keys": [
        {{
          "column": "string",
          "references_table": "string",
          "references_column": "string"
        }}
      ],
      "indexes": [
        {{
          "index_name": "string",
          "table_name": "string",
          "columns": ["string"],
          "unique": false
        }}
      ]
    }}
  ],
  "indexes": [
    {{
      "index_name": "string",
      "table_name": "string",
      "columns": ["string"],
      "unique": false
    }}
  ],
  "ddl": ["string"]
}}
""".strip()


def get_analytics_prompt(
    query: str,
    retrieved_candidates: list[dict[str, Any]],
    phase: str = "",
    brief_problem_statement: str = "",
    system_requirements: str = "",
) -> str:
    candidates_json = _compact_json(
        {
            "matching_phase": phase,
            "original_query": query,
            "brief_problem_statement": brief_problem_statement,
            "system_requirements": system_requirements,
            "retrieved_documents": retrieved_candidates,
        }
    )

    return f"""
You are a core banking glossary assistant for loan analytics.

Original query:
{query}

Retrieved candidates:
{candidates_json}

Return ONLY valid JSON.

Rules:
- Use only the retrieved global glossary candidates.
- Do not invent entities or attributes outside the retrieved documents.
- Judge relevance only from business meaning and glossary wording.
- Use the brief problem statement and system requirements only as supporting context.
- Do not let supporting context override the requested attribute itself.
- Keep a candidate only if that specific attribute directly answers the user's requested attribute.
- For every decision, assign semantic_score from 0.0 to 1.0 for business meaning similarity between the requested attribute and that specific candidate attribute.
- Use 1.0 only for a direct business synonym or exact same business concept; use lower scores for related but less exact candidates.
- Attribute synonyms are allowed when the business concept is the same.
- Accept common identifier wording such as `id`, `identifier`, `identification`, `reference`, and `key` when the subject also matches.
- Reject subject mismatches such as `customer` when the user asked for `facility`, or `loan` when the user asked for `customer`, unless the attribute itself directly answers the exact request.
- Reject neighboring attributes from the same entity if they are not the requested concept.
- Example: if the user asks for `customer id`, reject `customer_name`.
- Example: if the user asks for `facility identification`, reject `cust_id` even if the entity description mentions facilities.
- There is no layer restriction. CDA, GDA, or MDA can all be valid.
- If no candidate directly answers the query, keep none of them.
- Keep the answer short, clear, and business-friendly.

Required output:
{{
  "answer": "string",
  "decisions": [
    {{
      "doc_id": "string",
      "keep": true,
      "semantic_score": 0.0,
      "reason": "string"
    }}
  ]
}}
""".strip()
