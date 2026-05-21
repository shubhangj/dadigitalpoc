import re

#editd by mani
LOGICAL_COLUMN_MARKER = "\u200b"


def clean_name(name: str) -> str:
    if not name:
        return "UNKNOWN"

    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-zA-Z0-9_]", "", name)

    return name or "UNKNOWN"


def normalize_entity(name: str) -> str:
    return clean_name(name).upper()


def normalize_data_type(data_type: str, default_type: str = "string") -> str:
    if not data_type:
        return default_type

    data_type = data_type.strip().lower()
    data_type = data_type.replace("/", "_")
    data_type = re.sub(r"[^a-z0-9]+", "_", data_type)
    data_type = re.sub(r"_+", "_", data_type).strip("_")

    return data_type or default_type


def format_key_flags(is_primary_key: bool, is_foreign_key: bool) -> str:
    if is_primary_key and is_foreign_key:
        return " PK,FK"
    if is_primary_key:
        return " PK"
    if is_foreign_key:
        return " FK"
    return ""


def build_relationship_connector(primary_key: list[str], foreign_key_column: str) -> str:
    normalized_primary_keys = {clean_name(column).lower() for column in primary_key}
    normalized_foreign_key = clean_name(foreign_key_column).lower()

    if normalized_primary_keys == {normalized_foreign_key}:
        return "||--||"

    return "||--o{"


def get_connector(cardinality: str) -> str:
    if not cardinality:
        return "||--o{"

    cardinality = cardinality.replace(" ", "").upper()

    if cardinality in ["1:N", "1-M", "ONE_TO_MANY"]:
        return "||--o{"
    elif cardinality in ["N:1", "M-1", "MANY_TO_ONE"]:
        return "}o--||"
    elif cardinality in ["1:1", "ONE_TO_ONE"]:
        return "||--||"
    elif cardinality in ["M:N", "N:N", "M-M", "MANY_TO_MANY"]:
        return "}o--o{"


    return "||--o{"


def get_label(rel) -> str:
    if getattr(rel, "label", None):
        return clean_name(rel.label).lower()

    desc = getattr(rel, "description", "") or ""
    desc = desc.lower()

    if "own" in desc:
        return "owns"
    if "transaction" in desc:
        return "records"
    if "account" in desc:
        return "has"


    return clean_name(rel.to_entity).lower()


def build_mermaid(conceptual_model):
    lines = ["erDiagram"]

    
    for entity in conceptual_model.entities:
        entity_name = normalize_entity(entity.name)
        lines.append(f"  {entity_name} {{")
        lines.append("  }")

    
    for rel in conceptual_model.relationships:
        from_entity = normalize_entity(rel.from_entity)
        to_entity = normalize_entity(rel.to_entity)

        connector = get_connector(getattr(rel, "cardinality", ""))
        label = get_label(rel)

        lines.append(
            f"  {from_entity} {connector} {to_entity} : {label}"
        )

    return "\n".join(lines)


def build_logical_mermaid(logical_model):
    lines = ["erDiagram"]

    for table in logical_model.tables:
        table_name = normalize_entity(table.table_name)
        primary_keys = {clean_name(column).lower() for column in table.primary_key}
        foreign_keys = {
            clean_name(foreign_key.column).lower()
            for foreign_key in table.foreign_keys
        }

        lines.append(f"  {table_name} {{")
        for column in table.columns:
            column_name = clean_name(column.name).lower()
            key_flags = format_key_flags(
                column_name in primary_keys,
                column_name in foreign_keys,
            )
            lines.append(f"    {LOGICAL_COLUMN_MARKER} {column_name}{key_flags}")
        lines.append("  }")

    for table in logical_model.tables:
        child_table = normalize_entity(table.table_name)
        for foreign_key in table.foreign_keys:
            parent_table = normalize_entity(foreign_key.references_table)
            connector = build_relationship_connector(
                table.primary_key,
                foreign_key.column,
            )
            label = clean_name(foreign_key.column).lower()
            lines.append(f"  {parent_table} {connector} {child_table} : {label}")

    return "\n".join(lines)


def build_physical_mermaid(physical_model):
    lines = ["erDiagram"]

    for table in physical_model.tables:
        table_name = normalize_entity(table.table_name)
        primary_keys = {clean_name(column).lower() for column in table.primary_key}
        foreign_keys = {
            clean_name(foreign_key.column).lower()
            for foreign_key in table.foreign_keys
        }

        lines.append(f"  {table_name} {{")
        for column in table.columns:
            column_name = clean_name(column.name).lower()
            column_type = normalize_data_type(column.column_data_type, default_type="column")
            key_flags = format_key_flags(
                column_name in primary_keys,
                column_name in foreign_keys,
            )
            lines.append(f"    {column_type} {column_name}{key_flags}")
        lines.append("  }")

    for table in physical_model.tables:
        child_table = normalize_entity(table.table_name)
        for foreign_key in table.foreign_keys:
            parent_table = normalize_entity(foreign_key.references_table)
            connector = build_relationship_connector(
                table.primary_key,
                foreign_key.column,
            )
            label = clean_name(foreign_key.column).lower()
            lines.append(f"  {parent_table} {connector} {child_table} : {label}")

    return "\n".join(lines)
