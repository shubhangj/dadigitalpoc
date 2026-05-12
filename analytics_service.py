"""POC analytics attribute matcher.

Search order:
1. Exact GDA attribute match
2. Exact MDA plus fuzzy GDA, or semantic GDA when no fuzzy GDA exists
3. GDA-only fuzzy/semantic when no exact MDA exists
4. MDA-only exact when no GDA fuzzy/semantic candidate exists
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover
    ChatGoogleGenerativeAI = None

try:
    import faiss
except ImportError:  # pragma: no cover
    faiss = None

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None

try:
    from analytics_workbook import ensure_glossary_json
    from config import get_gemini_api_key, get_gemini_model
    from prompts import get_analytics_prompt
    from schemas import (
        AnalyticsLLMRelevanceSelection,
        AnalyticsLayerSummary,
        AnalyticsOutputMatch,
        AnalyticsResponse,
        AnalyticsRetrievalMetadata,
        AnalyticsVectorDocument,
    )
except ImportError:  # pragma: no cover
    from .analytics_workbook import ensure_glossary_json
    from .config import get_gemini_api_key, get_gemini_model
    from .prompts import get_analytics_prompt
    from .schemas import (
        AnalyticsLLMRelevanceSelection,
        AnalyticsLayerSummary,
        AnalyticsOutputMatch,
        AnalyticsResponse,
        AnalyticsRetrievalMetadata,
        AnalyticsVectorDocument,
    )


logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
ANALYTICS_OUTPUT_DIR = Path(tempfile.gettempdir()) / "HSBC-OminiAIDataFabric"
ANALYTICS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ANALYTICS_QUERY_OUTPUT_PATH = ANALYTICS_OUTPUT_DIR / "Analytics_Query_Output.json"
ANALYTICS_LINEAGE_XLSX_PATH = Path(__file__).with_name("DATA") / "updated_test_lineage.xlsx"
PHASE_BASE_WEIGHTS = {
    "phase1_exact": 0.9,
    "phase1_exact_mda_only": 0.75,
    "phase2_fuzzy": 0.52,
    "phase2_fuzzy_mda_only": 0.45,
    "phase3_semantic": 0.28,
    "phase3_semantic_mda_only": 0.22,
    "phase_cda_suggestion": 0.0,     # not a match — suggestion only
}
PHASE_MAX_WEIGHTS = {
    "phase1_exact": 1.0,
    "phase1_exact_mda_only": 0.89,
    "phase2_fuzzy": 0.89,
    "phase2_fuzzy_mda_only": 0.80,
    "phase3_semantic": 0.69,
    "phase3_semantic_mda_only": 0.60,
    "phase_cda_suggestion": 0.0,
}
LAYER_ORDER = ["CDA", "GDA", "MDA"]
CANDIDATE_LAYER_ORDER = ["GDA", "MDA", "CDA"]
LAYER_SCORE_WEIGHTS = {
    "GDA": 0.18,
    "MDA": 0.08,
    "CDA": 0.02,
}
SELECTED_VALUE_STREAM_BONUS = 0.06
REGION_METADATA_BONUS = 0.04
MAX_RETURNED_CANDIDATES = 3
MAX_PHASE3_MATCHES = 6
SEMANTIC_CANDIDATE_LIMIT = 20
LLM_RELEVANCE_CANDIDATE_LIMIT = 12
PHASE2_MIN_FUZZY = 0.86
PHASE3_MIN_SEMANTIC = 0.30
DESCRIPTION_OVERLAP_BONUS = 0.08
PHASE_LABELS = {
    "phase1_exact": "exact match",
    "phase1_exact_mda_only": "exact MDA match (no GDA found)",
    "phase2_fuzzy": "fuzzy abbreviation match",
    "phase2_fuzzy_mda_only": "fuzzy MDA match (no GDA found)",
    "phase3_semantic": "semantic fallback match",
    "phase3_semantic_mda_only": "semantic MDA match (no GDA found)",
    "phase_cda_suggestion": "CDA source found — derivation suggested",
}
ABBREVIATION_MAP = {
    "acct": "account",
    "addr": "address",
    "amt": "amount",
    "arr": "arrangement",
    "bal": "balance",
    "cd": "code",
    "cnt": "count",
    "coll": "collateral",
    "cust": "customer",
    "desc": "description",
    "dt": "date",
    "flg": "flag",
    "identification": "identifier",
    "id": "identifier",
    "ind": "indicator",
    "int": "interest",
    "kyc": "know_your_customer",
    "ln": "loan",
    "nbr": "number",
    "nm": "name",
    "no": "number",
    "num": "number",
    "pct": "percent",
    "prov": "provision",
    "qty": "quantity",
    "ref": "reference",
    "seg": "segment",
    "stat": "status",
    "sts": "status",
    "txn": "transaction",
    "typ": "type",
}
CONCEPT_FAMILIES = {
    "identifier": {"id", "identifier", "key", "reference", "ref", "number"},
    "name": {"name", "label", "title"},
    "date": {"date", "day", "month", "year", "timestamp"},
    "amount": {"amount", "balance", "value", "exposure", "limit", "principal", "outstanding"},
    "code": {"code"},
    "type": {"type", "category", "class", "segment"},
    "status": {"status", "state"},
    "flag": {"flag", "indicator"},
    "count": {"count", "quantity", "qty"},
    "rating": {"rating", "grade", "score"},
    "percent": {"percent", "percentage", "ratio", "rate"},
}
NON_DOMAIN_TOKENS = {
    "account",
    "amount",
    "balance",
    "category",
    "class",
    "code",
    "count",
    "date",
    "day",
    "description",
    "flag",
    "grade",
    "id",
    "identifier",
    "indicator",
    "key",
    "label",
    "limit",
    "month",
    "name",
    "number",
    "outstanding",
    "percent",
    "principal",
    "quantity",
    "rate",
    "rating",
    "ratio",
    "reference",
    "score",
    "segment",
    "state",
    "status",
    "timestamp",
    "title",
    "type",
    "value",
    "year",
}
TEXT_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "or",
    "the",
    "to",
    "with",
}

_analytics_index: "AnalyticsIndex | None" = None
_embedding_model: Any | None = None
_analytics_llm: Any | None = None
_analytics_lineage_records: list[dict[str, str]] | None = None


@dataclass
class GlossaryRecord:
    doc_id: str
    asset_category: str
    asset_name: str
    asset_attribute: str
    entity_name: str
    attribute_name: str
    attribute_description: str
    entity_description: str
    source_description: str
    lineage_assets: list[str]
    join_keys: list[str]
    region: str
    normalized_attribute: str
    expanded_attribute: str
    semantic_text: str


@dataclass
class AnalyticsIndex:
    records: list[GlossaryRecord]
    faiss_index: Any | None


@dataclass
class QueryProfile:
    normalized_attribute: str
    expanded_attribute: str
    compact_attribute: str
    compact_expanded_attribute: str
    attribute_tokens: set[str]
    description_tokens: set[str]
    concept_families: set[str]
    domain_tokens: set[str]


@dataclass
class AnalyticsSearchRequest:
    attribute_name: str
    attribute_description: str
    region: str
    original_query: str
    profile: QueryProfile
    selected_asset_name: str = ""
    brief_problem_statement: str = ""
    system_requirements: str = ""


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    return str(value).strip()


def _normalize_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")


def _compact_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _display_name(text: str) -> str:
    return _normalize_name(text).replace("_", " ").strip()


def _split_tokens(text: str) -> list[str]:
    return [token for token in _normalize_name(text).split("_") if token]


def _lineage_column_key(column: Any) -> str:
    return _normalize_name(_safe_text(column))


def load_analytics_lineage_records(path: Path | None = None) -> list[dict[str, str]]:
    """Read and cache MDA/GDA/CDA lineage rows from the sample lineage workbook."""
    global _analytics_lineage_records
    if _analytics_lineage_records is not None and path is None:
        return _analytics_lineage_records

    lineage_path = path or ANALYTICS_LINEAGE_XLSX_PATH
    if not lineage_path.exists():
        if path is None:
            _analytics_lineage_records = []
        return []

    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        logger.warning("pandas is required to read analytics lineage workbook.")
        if path is None:
            _analytics_lineage_records = []
        return []

    df = pd.read_excel(lineage_path)
    column_lookup = {_lineage_column_key(column): column for column in df.columns}
    required_columns = [
        "source_layer",
        "source_asset",
        "source_attribute",
        "target_layer",
        "target_asset",
        "target_attribute",
        "transformation_logic",
    ]
    missing_columns = [column for column in required_columns if column not in column_lookup]
    if missing_columns:
        raise ValueError(
            "Analytics lineage workbook is missing required column(s): "
            f"{', '.join(missing_columns)}"
        )

    records: list[dict[str, str]] = []
    for _, row in df.iterrows():
        record = {
            column: _safe_text(row.get(column_lookup[column], ""))
            for column in required_columns
        }
        if record["source_asset"] and record["target_asset"]:
            records.append(record)

    if path is None:
        _analytics_lineage_records = records
    return records


def _match_gda_lineage_details(match: AnalyticsOutputMatch) -> list[dict[str, str]]:
    if match.asset_category != "GDA":
        return []

    target_asset = _safe_text(match.asset_name)
    target_attribute = _safe_text(match.attribute_name)
    if not target_asset or not target_attribute:
        return []

    details: list[dict[str, str]] = []
    for record in load_analytics_lineage_records():
        if _safe_text(record.get("target_layer")).upper() != "GDA":
            continue
        if _safe_text(record.get("target_asset")) != target_asset:
            continue
        if _normalize_name(record.get("target_attribute")) != _normalize_name(target_attribute):
            continue
        details.append(record)
    return details


def _lineage_details_summary(lineage_details: list[dict[str, str]]) -> str:
    summary_parts: list[str] = []
    for detail in lineage_details:
        source = ".".join(
            part
            for part in [
                _safe_text(detail.get("source_asset")),
                _safe_text(detail.get("source_attribute")),
            ]
            if part
        )
        target = ".".join(
            part
            for part in [
                _safe_text(detail.get("target_asset")),
                _safe_text(detail.get("target_attribute")),
            ]
            if part
        )
        transformation = _safe_text(detail.get("transformation_logic"))
        if source and target and transformation:
            summary_parts.append(f"{source} -> {target}: {transformation}")
        elif source and target:
            summary_parts.append(f"{source} -> {target}")
    return " | ".join(summary_parts)


def enrich_gda_matches_with_lineage(matches: list[AnalyticsOutputMatch]) -> list[AnalyticsOutputMatch]:
    for match in matches:
        lineage_details = _match_gda_lineage_details(match)
        if not lineage_details:
            continue
        match.lineage_details = lineage_details
        match.lineage_assets = list(
            dict.fromkeys(
                _safe_text(detail.get("source_asset"))
                for detail in lineage_details
                if _safe_text(detail.get("source_asset"))
            )
        )
        lineage_summary = _lineage_details_summary(lineage_details)
        if lineage_summary:
            match.source_description = lineage_summary
    return matches


def _expand_attribute_name(text: str) -> str:
    expanded_tokens: list[str] = []
    for token in _split_tokens(text):
        replacement = ABBREVIATION_MAP.get(token, token)
        expanded_tokens.extend(part for part in replacement.split("_") if part)
    return "_".join(expanded_tokens)


def _token_set(text: str) -> set[str]:
    return {token for token in _split_tokens(text) if token}


def _concept_families_from_tokens(tokens: set[str]) -> set[str]:
    families = set()
    for family, family_tokens in CONCEPT_FAMILIES.items():
        if tokens.intersection(family_tokens):
            families.add(family)
    return families


def _domain_tokens_from_tokens(tokens: set[str]) -> set[str]:
    return {
        token
        for token in tokens
        if len(token) > 2
        and token not in NON_DOMAIN_TOKENS
        and token not in TEXT_STOPWORDS
    }


def _build_query_profile(attribute_name: str, attribute_description: str) -> QueryProfile:
    normalized_attribute = _normalize_name(attribute_name)
    expanded_attribute = _expand_attribute_name(attribute_name)
    attribute_tokens = _token_set(expanded_attribute)
    description_tokens = _token_set(attribute_description)
    concept_families = _concept_families_from_tokens(attribute_tokens.union(description_tokens))
    domain_tokens = _domain_tokens_from_tokens(attribute_tokens.union(description_tokens))
    return QueryProfile(
        normalized_attribute=normalized_attribute,
        expanded_attribute=expanded_attribute,
        compact_attribute=_compact_name(normalized_attribute),
        compact_expanded_attribute=_compact_name(expanded_attribute),
        attribute_tokens=attribute_tokens,
        description_tokens=description_tokens,
        concept_families=concept_families,
        domain_tokens=domain_tokens,
    )


def _build_search_request(
    attribute_name: str,
    attribute_description: str = "",
    region: str = "",
    selected_asset_name: str = "",
    brief_problem_statement: str = "",
    system_requirements: str = "",
) -> AnalyticsSearchRequest:
    clean_attribute = _safe_text(attribute_name)
    clean_description = _safe_text(attribute_description)
    clean_region = _safe_text(region).upper()
    clean_selected_asset_name = _safe_text(selected_asset_name)
    clean_brief_problem_statement = _safe_text(brief_problem_statement)
    clean_system_requirements = _safe_text(system_requirements)

    if not clean_attribute:
        raise ValueError("attribute_name is required for analytics search.")

    return AnalyticsSearchRequest(
        attribute_name=clean_attribute,
        attribute_description=clean_description,
        region=clean_region,
        original_query=_build_query_text(clean_attribute, clean_description, clean_region),
        profile=_build_query_profile(clean_attribute, clean_description),
        selected_asset_name=clean_selected_asset_name,
        brief_problem_statement=clean_brief_problem_statement,
        system_requirements=clean_system_requirements,
    )


def _resolve_glossary_json_path() -> Path:
    return ensure_glossary_json()


def _get_embedding_model() -> Any | None:
    global _embedding_model
    if SentenceTransformer is None:
        return None
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def _get_analytics_llm() -> Any | None:
    global _analytics_llm
    if _analytics_llm is not None:
        return _analytics_llm

    api_key = get_gemini_api_key()
    if not api_key or ChatGoogleGenerativeAI is None:
        return None

    _analytics_llm = ChatGoogleGenerativeAI(
        model=get_gemini_model(),
        google_api_key=api_key,
        temperature=0,
        max_retries=0,
        timeout=30,
    )
    return _analytics_llm


def _record_from_document(document: AnalyticsVectorDocument) -> GlossaryRecord:
    semantic_text = " | ".join(
        part
        for part in [
            _display_name(document.attribute_name),
            _safe_text(document.attribute_description),
            _display_name(document.entity_name),
            _safe_text(document.entity_description),
        ]
        if part
    )
    return GlossaryRecord(
        doc_id=document.doc_id,
        asset_category=_safe_text(document.asset_category).upper(),
        asset_name=_safe_text(document.asset_name),
        asset_attribute=_safe_text(document.asset_attribute),
        entity_name=_safe_text(document.entity_name),
        attribute_name=_safe_text(document.attribute_name),
        attribute_description=_safe_text(document.attribute_description),
        entity_description=_safe_text(document.entity_description),
        source_description=_safe_text(document.source_description),
        lineage_assets=[
            _safe_text(asset)
            for asset in (document.lineage_assets or [])
            if _safe_text(asset)
        ],
        join_keys=[
            _safe_text(join_key)
            for join_key in (document.join_keys or [])
            if _safe_text(join_key)
        ],
        region=_safe_text(document.physical_region).upper(),
        normalized_attribute=_normalize_name(document.attribute_name),
        expanded_attribute=_expand_attribute_name(document.attribute_name),
        semantic_text=semantic_text,
    )


def _load_glossary_records() -> list[GlossaryRecord]:
    source_path = _resolve_glossary_json_path()
    documents = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(documents, list) or not documents:
        raise ValueError("Analytics glossary JSON must contain a non-empty list of documents.")

    records: list[GlossaryRecord] = []
    for item in documents:
        records.append(_record_from_document(AnalyticsVectorDocument.model_validate(item)))
    return records


def _build_faiss_index(records: list[GlossaryRecord]) -> Any | None:
    if not records or faiss is None:
        return None

    model = _get_embedding_model()
    if model is None:
        return None

    embeddings = model.encode(
        [record.semantic_text for record in records],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings.astype("float32"))
    return index


def _get_analytics_index() -> AnalyticsIndex:
    global _analytics_index
    if _analytics_index is None:
        records = _load_glossary_records()
        _analytics_index = AnalyticsIndex(
            records=records,
            faiss_index=_build_faiss_index(records),
        )
    return _analytics_index


def warm_analytics_index() -> None:
    _get_analytics_index()


def _candidate_records_for_region(
    index: AnalyticsIndex,
    region: str,
) -> tuple[list[tuple[int, GlossaryRecord]], list[GlossaryRecord]]:
    candidate_positions: list[tuple[int, GlossaryRecord]] = [
        (position, record)
        for position, record in enumerate(index.records)
        if not region or record.region == region or not record.region  # include untagged global records
    ]
    return candidate_positions, [record for _, record in candidate_positions]


def _build_retrieval_metadata(
    index: AnalyticsIndex,
    candidate_records: list[GlossaryRecord],
) -> AnalyticsRetrievalMetadata:
    return AnalyticsRetrievalMetadata(
        documents_considered=len(index.records),
        region_filtered_documents=len(candidate_records),
        semantic_index_enabled=index.faiss_index is not None,
    )


def _build_query_text(attribute_name: str, attribute_description: str, region: str) -> str:
    parts = [attribute_name.strip(), attribute_description.strip()]
    if region.strip():
        parts.append(f"region {region.strip()}")
    return " | ".join(part for part in parts if part)


def _rapidfuzz_score(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if fuzz is None:
        if left == right:
            return 1.0
        return 0.0
    return max(
        fuzz.ratio(left, right),
        fuzz.partial_ratio(left, right),
        fuzz.token_sort_ratio(left, right),
        fuzz.token_set_ratio(left, right),
    ) / 100.0


def _semantic_score_map(index: AnalyticsIndex, query_text: str) -> dict[int, float]:
    if not query_text:
        return {}

    if index.faiss_index is None:
        query_tokens = _token_set(query_text)
        score_map: dict[int, float] = {}
        for position, record in enumerate(index.records):
            record_tokens = _token_set(record.semantic_text)
            overlap_ratio = (
                len(query_tokens.intersection(record_tokens)) / max(len(query_tokens), 1)
                if query_tokens
                else 0.0
            )
            text_similarity = _rapidfuzz_score(query_text.lower(), record.semantic_text.lower())
            fallback_score = min(1.0, (0.55 * text_similarity) + (0.45 * overlap_ratio))
            score_map[position] = round(fallback_score, 6)
        return score_map

    model = _get_embedding_model()
    if model is None:
        return {}

    query_vector = model.encode(
        [query_text],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")
    distances, indices = index.faiss_index.search(query_vector, len(index.records))

    score_map: dict[int, float] = {}
    for score, position in zip(distances[0].tolist(), indices[0].tolist()):
        if position < 0:
            continue
        score_map[position] = round(max(0.0, min(1.0, float(score))), 6)
    return score_map


def _record_concept_families(record: GlossaryRecord) -> set[str]:
    return _concept_families_from_tokens(
        _token_set(record.expanded_attribute).union(
            _token_set(record.attribute_description),
            _token_set(record.entity_name),
            _token_set(record.entity_description),
        )
    )


def _record_domain_tokens(record: GlossaryRecord) -> set[str]:
    return _domain_tokens_from_tokens(
        _token_set(record.expanded_attribute).union(
            _token_set(record.attribute_description),
            _token_set(record.entity_name),
            _token_set(record.entity_description),
        )
    )


def _domain_overlap_count(profile: QueryProfile, record: GlossaryRecord) -> int:
    if not profile.domain_tokens:
        return 0
    return len(profile.domain_tokens.intersection(_record_domain_tokens(record)))


def _description_alignment(profile: QueryProfile, record: GlossaryRecord) -> float:
    if not profile.description_tokens:
        return 0.0

    record_tokens = (
        _token_set(record.attribute_description)
        .union(_token_set(record.entity_description))
        .union(_token_set(record.expanded_attribute))
    )
    if not record_tokens:
        return 0.0

    overlap = len(profile.description_tokens.intersection(record_tokens))
    return round(overlap / max(len(profile.description_tokens), 1), 6)


def _attribute_variants(*values: str) -> set[str]:
    variants: set[str] = set()
    for value in values:
        safe_value = _safe_text(value)
        if safe_value:
            variants.add(safe_value)
            compact_value = _compact_name(safe_value)
            if compact_value:
                variants.add(compact_value)
    return variants


def _best_phase2_score(profile: QueryProfile, record: GlossaryRecord) -> tuple[float, bool]:
    query_variants = _attribute_variants(
        profile.normalized_attribute,
        profile.expanded_attribute,
        profile.compact_attribute,
        profile.compact_expanded_attribute,
    )
    record_variants = _attribute_variants(
        record.normalized_attribute,
        record.expanded_attribute,
    )

    best_score = 0.0
    direct_compact_match = False
    for query_variant in query_variants:
        query_compact = _compact_name(query_variant)
        for record_variant in record_variants:
            if query_compact and query_compact == _compact_name(record_variant):
                direct_compact_match = True
                best_score = 1.0
                continue
            score = _rapidfuzz_score(
                query_variant.replace("_", " "),
                record_variant.replace("_", " "),
            )
            if score > best_score:
                best_score = score

    return best_score, direct_compact_match


def _passes_relevance_checklist(
    profile: QueryProfile,
    record: GlossaryRecord,
    phase: str,
    fuzzy_score: float = 0.0,
    semantic_score: float = 0.0,
) -> bool:
    record_concepts = _record_concept_families(record)
    concept_overlap = profile.concept_families.intersection(record_concepts)
    domain_overlap = _domain_overlap_count(profile, record)
    attribute_token_overlap = len(profile.attribute_tokens.intersection(_token_set(record.expanded_attribute)))

    if profile.concept_families and record_concepts and not concept_overlap:
        return False

    if "identifier" in profile.concept_families and "identifier" not in record_concepts:
        return False
    if "name" in profile.concept_families and "name" not in record_concepts:
        return False
    if "date" in profile.concept_families and "date" not in record_concepts:
        return False
    if "amount" in profile.concept_families and "amount" not in record_concepts:
        return False
    if "code" in profile.concept_families and "code" not in record_concepts:
        return False

    if profile.domain_tokens and domain_overlap == 0 and attribute_token_overlap == 0:
        return False

    if phase == "phase2_fuzzy":
        return fuzzy_score >= PHASE2_MIN_FUZZY or profile.expanded_attribute == record.expanded_attribute

    if phase == "phase3_semantic":
        return semantic_score >= PHASE3_MIN_SEMANTIC and (domain_overlap > 0 or not profile.domain_tokens)

    return True


def _match_weight(
    match_phase: str,
    domain_overlap: int,
    description_alignment: float,
    fuzzy_score: float = 0.0,
    semantic_score: float = 0.0,
) -> float:
    domain_bonus = min(0.08, domain_overlap * 0.02)
    description_bonus = min(0.08, description_alignment * 0.08)
    base_weight = PHASE_BASE_WEIGHTS.get(match_phase, 0.3)

    if match_phase == "phase1_exact":
        return round(min(1.0, base_weight + domain_bonus + description_bonus), 4)

    if match_phase == "phase2_fuzzy":
        fuzzy_bonus = min(0.24, fuzzy_score * 0.24)
        return round(min(0.89, base_weight + fuzzy_bonus + domain_bonus + description_bonus), 4)

    semantic_bonus = min(0.26, semantic_score * 0.26)
    return round(min(0.69, base_weight + semantic_bonus + domain_bonus + description_bonus), 4)


def _build_transformation_suggestion(
    record: GlossaryRecord,
    query_attribute: str,
    query_description: str,
    match_phase: str,
) -> str:
    """
    Generates a plain-English transformation suggestion + SQL snippet
    for MDA-only matches where no GDA attribute exists yet.
    Only called when match_phase is an mda_only phase.
    """
    source_table = record.asset_name or "MDA.<source_table>"
    source_col   = record.attribute_name
    target_col   = re.sub(r"[^a-z0-9]+", "_", query_attribute.lower()).strip("_")

    suggestion = (
        f"No GDA attribute found for '{query_attribute}'. "
        f"Suggested transformation: derive '{target_col}' from "
        f"'{source_table}.{source_col}' in MDA. "
        f"This attribute is described as: {query_description}. "
        f"A GDA enhancement request should be raised to promote this to the authoritative layer."
    )

    sql = (
        f"-- Transformation suggestion for: {query_attribute}\n"
        f"-- Source: {source_table}.{source_col} (MDA)\n"
        f"-- Target: GDA.{target_col} (to be created via GDA enhancement)\n"
        f"SELECT\n"
        f"    {source_col} AS {target_col}\n"
        f"FROM {source_table}\n"
        f"WHERE {source_col} IS NOT NULL;"
    )

    return f"{suggestion}\n\nSuggested SQL:\n{sql}"


def _compute_recommendation_score(
    match_phase: str,
    phase_weight: float,
    layer: str,
    region_bonus: float,
) -> tuple[float, float, float]:
    """
    Single source of truth for score computation.
    Returns (raw_score, max_score, recommendation_score_pct).
    Called once per match — result fed into both the header card and the breakdown text.
    """
    layer_score = LAYER_SCORE_WEIGHTS.get(layer, 0.0)
    max_score = round(
        PHASE_MAX_WEIGHTS.get(match_phase, 1.0)
        + max(LAYER_SCORE_WEIGHTS.values())
        + REGION_METADATA_BONUS,
        4,
    )
    raw_score = round(phase_weight + layer_score + region_bonus, 4)
    if raw_score <= 0 or max_score <= 0:
        pct = 0.0
    else:
        pct = round(min(100.0, max(1.0, (raw_score / max_score) * 100)), 2)
    return raw_score, max_score, pct


def _build_score_breakdown(
    match_phase: str,
    phase_weight: float,
    recommendation_score: float,
    raw_score: float,
    max_score: float,
    fuzzy_score: float = 0.0,
    semantic_score: float = 0.0,
    domain_overlap: int = 0,
    description_alignment: float = 0.0,
    layer: str = "",
    region_bonus: float = 0.0,
) -> str:
    """
    Produces the breakdown text using the SAME values already used to compute
    recommendation_score. Header and breakdown are guaranteed to match because
    they share one calculation path via _compute_recommendation_score.
    """
    layer_score = LAYER_SCORE_WEIGHTS.get(layer, 0.0)
    base_weight = PHASE_BASE_WEIGHTS.get(match_phase, 0.3)

    lines = [f"Score Breakdown (how {recommendation_score}% is reached):"]

    # Phase weight components
    lines.append(f"  Base weight ({match_phase}): {base_weight}")
    if fuzzy_score:
        fb = round(min(0.24, fuzzy_score * 0.24), 4)
        lines.append(f"  + Fuzzy bonus ({round(fuzzy_score * 100, 1)}% x 0.24, cap 0.24): +{fb}")
    if semantic_score:
        sb = round(min(0.26, semantic_score * 0.26), 4)
        lines.append(f"  + Semantic bonus ({round(semantic_score * 100, 1)}% x 0.26, cap 0.26): +{sb}")
    if domain_overlap:
        db = round(min(0.08, domain_overlap * 0.02), 4)
        lines.append(f"  + Domain overlap ({domain_overlap} tokens x 0.02, cap 0.08): +{db}")
    if description_alignment:
        dab = round(min(0.08, description_alignment * 0.08), 4)
        lines.append(f"  + Description alignment ({round(description_alignment * 100, 1)}% x 0.08, cap 0.08): +{dab}")
    lines.append(f"  = Phase weight (capped at {PHASE_MAX_WEIGHTS.get(match_phase, 1.0)}): {round(phase_weight, 4)}")

    # Raw score assembly
    lines.append(f"  + Layer score ({layer}): +{round(layer_score, 4)}")
    if region_bonus:
        lines.append(f"  + Region match bonus: +{round(region_bonus, 4)}")
    lines.append(f"  = Raw score: {raw_score}")
    lines.append(f"  / Max possible ({round(PHASE_MAX_WEIGHTS.get(match_phase, 1.0), 2)} + 0.18 + 0.04): {max_score}")
    lines.append(f"  = Recommendation score: {recommendation_score}%")
    return "\n".join(lines)


def _build_justification(
    record: GlossaryRecord,
    match_phase: str,
    query_attribute: str,
    query_description: str,
    recommendation_score: float,
    raw_score: float,
    max_score: float,
    phase_weight: float,
    fuzzy_score: float = 0.0,
    semantic_score: float = 0.0,
    expanded_query: str = "",
    domain_overlap: int = 0,
    description_alignment: float = 0.0,
    region_bonus: float = 0.0,
) -> str:
    if match_phase == "phase1_exact":
        base = f"Exact match to \'{record.attribute_name}\'."
    elif match_phase in ("phase2_fuzzy", "phase2_fuzzy_mda_only"):
        if expanded_query and expanded_query == record.expanded_attribute:
            base = f"Normalized match to \'{record.attribute_name}\'."
        else:
            base = f"Fuzzy match to \'{record.attribute_name}\'."
        if match_phase == "phase2_fuzzy_mda_only":
            base += "\n\n" + _build_transformation_suggestion(record, query_attribute, query_description, match_phase)
    elif match_phase in ("phase3_semantic", "phase3_semantic_mda_only"):
        base = f"Semantic match to \'{record.attribute_name}\' after relevance check."
        if match_phase == "phase3_semantic_mda_only":
            base += "\n\n" + _build_transformation_suggestion(record, query_attribute, query_description, match_phase)
    elif match_phase == "phase1_exact_mda_only":
        base = f"Exact match to \'{record.attribute_name}\' in MDA (no GDA equivalent found)."
        base += "\n\n" + _build_transformation_suggestion(record, query_attribute, query_description, match_phase)
    else:
        base = f"Semantic match to \'{record.attribute_name}\' after relevance check."

    breakdown = _build_score_breakdown(
        match_phase=match_phase,
        phase_weight=phase_weight,
        recommendation_score=recommendation_score,
        raw_score=raw_score,
        max_score=max_score,
        fuzzy_score=fuzzy_score,
        semantic_score=semantic_score,
        domain_overlap=domain_overlap,
        description_alignment=description_alignment,
        layer=record.asset_category,
        region_bonus=region_bonus,
    )
    return f"{base}\n\n{breakdown}"


def _build_match(
    record: GlossaryRecord,
    match_phase: str,
    justification: str,
    internal_rank: float,
    phase_weight: float,
    recommendation_score: float = 0.0,
    fuzzy_score: float = 0.0,
    semantic_score: float = 0.0,
) -> AnalyticsOutputMatch:
    return AnalyticsOutputMatch(
        doc_id=record.doc_id,
        asset_category=record.asset_category,
        asset_name=record.asset_name,
        asset_attribute=record.asset_attribute,
        entity_name=record.entity_name,
        entity_description=record.entity_description,
        attribute_name=record.attribute_name,
        attribute_description=record.attribute_description,
        source_description=record.source_description,
        lineage_assets=record.lineage_assets,
        join_keys=record.join_keys,
        region=record.region,
        match_phase=match_phase,
        phase_weight=phase_weight,
        fuzzy_score=round(fuzzy_score, 6),
        semantic_score=round(semantic_score, 6),
        justification=justification,
        relevance_score=internal_rank,
        recommendation_score=recommendation_score,
    )


def _sort_matches(matches: list[AnalyticsOutputMatch]) -> list[AnalyticsOutputMatch]:
    return sorted(
        matches,
        key=lambda match: (
            -match.relevance_score,
            CANDIDATE_LAYER_ORDER.index(match.asset_category)
            if match.asset_category in CANDIDATE_LAYER_ORDER
            else len(CANDIDATE_LAYER_ORDER),
            match.asset_name,
            match.attribute_name,
        ),
    )


def _candidate_layer_score(match: AnalyticsOutputMatch) -> float:
    return LAYER_SCORE_WEIGHTS.get(match.asset_category, 0.0)


def _apply_candidate_scoring(
    matches: list[AnalyticsOutputMatch],
    request: AnalyticsSearchRequest,
) -> list[AnalyticsOutputMatch]:
    # Score is already computed per-match inside _find_phaseX_matches via
    # _compute_recommendation_score — single source of truth.
    # This function only sorts so the best match is first.
    return _sort_matches(matches)


def _gda_matches(matches: list[AnalyticsOutputMatch]) -> list[AnalyticsOutputMatch]:
    return [match for match in matches if match.asset_category == "GDA"]


def _gda_asset_names(matches: list[AnalyticsOutputMatch]) -> list[str]:
    asset_names: list[str] = []
    for match in matches:
        if match.asset_category != "GDA" or not match.asset_name:
            continue
        if match.asset_name not in asset_names:
            asset_names.append(match.asset_name)
    return asset_names


def _asset_selection_key(asset_name: str) -> str:
    parts = [part for part in _normalize_name(asset_name).split("_") if part]
    while parts and parts[0] in {"cda", "gda", "mda"}:
        parts = parts[1:]
    return "_".join(parts)


def _resolve_selected_asset_name(
    matches: list[AnalyticsOutputMatch],
    selected_asset_name: str,
    asset_category: str = "GDA",
) -> str:
    if not selected_asset_name:
        return ""

    selected_key = _asset_selection_key(selected_asset_name)
    for match in matches:
        if match.asset_category != asset_category or not match.asset_name:
            continue
        if match.asset_name == selected_asset_name:
            return match.asset_name
        if selected_key and _asset_selection_key(match.asset_name) == selected_key:
            return match.asset_name
    return ""


def _resolve_selected_asset_name_any(
    matches: list[AnalyticsOutputMatch],
    selected_asset_name: str,
) -> str:
    if not selected_asset_name:
        return ""

    for asset_category in ("GDA", "MDA", "CDA"):
        resolved = _resolve_selected_asset_name(matches, selected_asset_name, asset_category)
        if resolved:
            return resolved
    return ""


def _merge_matches(*match_groups: list[AnalyticsOutputMatch]) -> list[AnalyticsOutputMatch]:
    merged: list[AnalyticsOutputMatch] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for matches in match_groups:
        for match in matches:
            match_key = (
                _safe_text(match.asset_category),
                _safe_text(match.asset_name),
                _safe_text(match.entity_name),
                _safe_text(match.attribute_name),
                _safe_text(match.region),
            )
            if match_key in seen:
                continue
            seen.add(match_key)
            merged.append(match)
    return _sort_matches(merged)


def _records_for_layer(
    candidate_records: list[GlossaryRecord],
    asset_category: str,
) -> list[GlossaryRecord]:
    return [record for record in candidate_records if record.asset_category == asset_category]


def _positions_for_layer(
    candidate_positions: list[tuple[int, GlossaryRecord]],
    asset_category: str,
) -> list[tuple[int, GlossaryRecord]]:
    return [
        (position, record)
        for position, record in candidate_positions
        if record.asset_category == asset_category
    ]


def _semantic_scores_by_doc_id(
    candidate_positions: list[tuple[int, GlossaryRecord]],
    semantic_scores: dict[int, float],
) -> dict[str, float]:
    return {
        record.doc_id: semantic_scores.get(position, 0.0)
        for position, record in candidate_positions
    }


def _apply_semantic_scores_to_matches(
    matches: list[AnalyticsOutputMatch],
    semantic_scores_by_doc_id: dict[str, float],
) -> list[AnalyticsOutputMatch]:
    for match in matches:
        if match.match_phase == "phase1_exact":
            continue
        if match.semantic_score > 0:
            continue
        match.semantic_score = round(semantic_scores_by_doc_id.get(match.doc_id, 0.0), 6)
    return matches


def _rank_candidate_matches(
    request: AnalyticsSearchRequest,
    *match_groups: list[AnalyticsOutputMatch],
) -> list[AnalyticsOutputMatch]:
    return _apply_candidate_scoring(_merge_matches(*match_groups), request)[:MAX_RETURNED_CANDIDATES]


def _filter_matches_for_selected_asset(
    matches: list[AnalyticsOutputMatch],
    selected_asset_name: str,
) -> list[AnalyticsOutputMatch]:
    if not selected_asset_name:
        return matches

    selected_matches = [
        match
        for match in matches
        if match.asset_name == selected_asset_name
    ]
    if not selected_matches:
        selected_key = _asset_selection_key(selected_asset_name)
        selected_matches = [
            match
            for match in matches
            if match.asset_name and _asset_selection_key(match.asset_name) == selected_key
        ]
    if not selected_matches:
        return matches

    selected_keys = {match.doc_id for match in selected_matches}
    remaining_relevant_matches = [
        match
        for match in matches
        if match.doc_id not in selected_keys
    ]
    return selected_matches + remaining_relevant_matches


def _build_layer_summary(matches: list[AnalyticsOutputMatch]) -> list[AnalyticsLayerSummary]:
    counts: dict[str, int] = {}
    for match in matches:
        counts[match.asset_category] = counts.get(match.asset_category, 0) + 1
    ordered_layers = [layer for layer in LAYER_ORDER if layer in counts] + sorted(
        layer for layer in counts if layer not in LAYER_ORDER
    )
    return [
        AnalyticsLayerSummary(layer=layer, relevant_match_count=counts[layer])
        for layer in ordered_layers
    ]


def _slim_match(match: AnalyticsOutputMatch) -> AnalyticsOutputMatch:
    return AnalyticsOutputMatch(
        asset_category=match.asset_category,
        asset_name=match.asset_name,
        asset_attribute=match.asset_attribute,
        entity_name=match.entity_name,
        entity_description=match.entity_description,
        attribute_name=match.attribute_name,
        attribute_description=match.attribute_description,
        source_description=match.source_description,
        lineage_assets=match.lineage_assets,
        lineage_details=match.lineage_details,
        join_keys=match.join_keys,
        region=match.region,
        match_phase=match.match_phase,
        phase_weight=match.phase_weight,
        recommendation_score=match.recommendation_score,
        justification=match.justification,
    )


def _slim_match_payload(match: AnalyticsOutputMatch) -> dict[str, Any]:
    return _slim_match(match).model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
        exclude_defaults=True,
    )


def _find_phase1_matches(
    candidate_records: list[GlossaryRecord],
    profile: QueryProfile,
    query_attribute: str,
    query_description: str,
    region: str,
) -> list[AnalyticsOutputMatch]:
    matches: list[AnalyticsOutputMatch] = []
    for record in candidate_records:
        if profile.normalized_attribute != record.normalized_attribute:
            continue
        domain_overlap = _domain_overlap_count(profile, record)
        overlap_bonus = domain_overlap * DESCRIPTION_OVERLAP_BONUS
        description_alignment = _description_alignment(profile, record)
        phase_weight = _match_weight(
            match_phase="phase1_exact",
            domain_overlap=domain_overlap,
            description_alignment=description_alignment,
        )
        region_bonus = REGION_METADATA_BONUS if region and record.region == region else 0.0
        raw_score, max_score, recommendation_score = _compute_recommendation_score(
            match_phase="phase1_exact",
            phase_weight=phase_weight,
            layer=record.asset_category,
            region_bonus=region_bonus,
        )
        justification = _build_justification(
            record=record,
            match_phase="phase1_exact",
            query_attribute=query_attribute,
            query_description=query_description,
            recommendation_score=recommendation_score,
            raw_score=raw_score,
            max_score=max_score,
            phase_weight=phase_weight,
            domain_overlap=domain_overlap,
            description_alignment=description_alignment,
            region_bonus=region_bonus,
        )
        matches.append(
            _build_match(
                record=record,
                match_phase="phase1_exact",
                justification=justification,
                internal_rank=1.0 + overlap_bonus + description_alignment,
                phase_weight=phase_weight,
                recommendation_score=recommendation_score,
            )
        )
    return _sort_matches(matches)


def _find_phase2_matches(
    candidate_records: list[GlossaryRecord],
    profile: QueryProfile,
    query_attribute: str,
    query_description: str,
    region: str,
) -> list[AnalyticsOutputMatch]:
    matches: list[AnalyticsOutputMatch] = []
    for record in candidate_records:
        fuzzy_score, direct_compact_match = _best_phase2_score(profile, record)
        if not _passes_relevance_checklist(
            profile=profile,
            record=record,
            phase="phase2_fuzzy",
            fuzzy_score=fuzzy_score,
        ):
            continue

        domain_overlap = _domain_overlap_count(profile, record)
        overlap_bonus = domain_overlap * DESCRIPTION_OVERLAP_BONUS
        description_alignment = _description_alignment(profile, record)
        phase_weight = _match_weight(
            match_phase="phase2_fuzzy",
            domain_overlap=domain_overlap,
            description_alignment=description_alignment,
            fuzzy_score=fuzzy_score,
        )
        region_bonus = REGION_METADATA_BONUS if region and record.region == region else 0.0
        raw_score, max_score, recommendation_score = _compute_recommendation_score(
            match_phase="phase2_fuzzy",
            phase_weight=phase_weight,
            layer=record.asset_category,
            region_bonus=region_bonus,
        )
        justification = _build_justification(
            record=record,
            match_phase="phase2_fuzzy",
            query_attribute=query_attribute,
            query_description=query_description,
            recommendation_score=recommendation_score,
            raw_score=raw_score,
            max_score=max_score,
            phase_weight=phase_weight,
            fuzzy_score=fuzzy_score,
            expanded_query=profile.expanded_attribute,
            domain_overlap=domain_overlap,
            description_alignment=description_alignment,
            region_bonus=region_bonus,
        )
        if direct_compact_match:
            lines = justification.split("\n\n", 1)
            first_line = lines[0]
            rest = "\n\n" + lines[1] if len(lines) > 1 else ""
            first_line = f"{first_line[:-1]} via compact form." if first_line.endswith(".") else f"{first_line} via compact form."
            justification = first_line + rest
        matches.append(
            _build_match(
                record=record,
                match_phase="phase2_fuzzy",
                justification=justification,
                internal_rank=fuzzy_score + overlap_bonus + description_alignment,
                phase_weight=phase_weight,
                fuzzy_score=fuzzy_score,
                recommendation_score=recommendation_score,
            )
        )
    return _sort_matches(matches)


def _dedupe_matches_by_entity(matches: list[AnalyticsOutputMatch]) -> list[AnalyticsOutputMatch]:
    deduped: list[AnalyticsOutputMatch] = []
    seen: set[tuple[str, str, str]] = set()
    for match in matches:
        entity_key = (
            _safe_text(match.asset_category),
            _safe_text(match.entity_name) or _safe_text(match.asset_name),
            _safe_text(match.region),
        )
        if entity_key in seen:
            continue
        seen.add(entity_key)
        deduped.append(match)
    return deduped


def _semantic_focus_tokens(profile: QueryProfile) -> set[str]:
    focus_tokens = _domain_tokens_from_tokens(profile.attribute_tokens)
    if focus_tokens:
        return focus_tokens
    return profile.domain_tokens


def _strict_semantic_attribute_filter(
    matches: list[AnalyticsOutputMatch],
    profile: QueryProfile,
) -> list[AnalyticsOutputMatch]:
    filtered: list[AnalyticsOutputMatch] = []
    focus_tokens = _semantic_focus_tokens(profile)

    for match in matches:
        attribute_tokens = _token_set(_expand_attribute_name(match.attribute_name))
        description_tokens = _token_set(match.attribute_description)
        attribute_surface_tokens = attribute_tokens.union(description_tokens)
        record_concepts = _concept_families_from_tokens(attribute_surface_tokens)

        if profile.concept_families and record_concepts and not profile.concept_families.intersection(record_concepts):
            continue
        if focus_tokens and not focus_tokens.intersection(attribute_surface_tokens):
            continue
        filtered.append(match)

    return filtered


def _llm_candidate_payload(matches: list[AnalyticsOutputMatch]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for match in matches[:LLM_RELEVANCE_CANDIDATE_LIMIT]:
        payload.append(
            {
                "doc_id": match.doc_id,
                "asset_category": match.asset_category,
                "asset_name": match.asset_name,
                "asset_attribute": match.asset_attribute,
                "entity_name": match.entity_name,
                "value_stream": match.entity_name,
                "attribute_name": match.attribute_name,
                "attribute_description": match.attribute_description,
                "entity_description": match.entity_description,
                "region": match.region,
                "match_phase": match.match_phase,
                "phase_weight": round(match.phase_weight, 4),
                "fuzzy_score": round(match.fuzzy_score, 4),
                "semantic_score": round(match.semantic_score, 4),
            }
        )
    return payload


def _should_run_llm_filter(
    matches: list[AnalyticsOutputMatch],
    request: AnalyticsSearchRequest,
    phase: str,
) -> bool:
    if not matches:
        return False
    has_context = bool(request.brief_problem_statement or request.system_requirements)
    if phase == "phase3_semantic":
        return True
    if phase == "phase1_exact":
        return len(matches) > 1 and has_context
    if phase == "phase2_fuzzy":
        return len(matches) > 1 or has_context
    return False


def _llm_query_text(request: AnalyticsSearchRequest) -> str:
    return _build_query_text(
        request.attribute_name,
        request.attribute_description,
        request.region,
    )


def _clamp_similarity_score(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(max(0.0, min(1.0, float(value))), 6)
    except (TypeError, ValueError):
        return None


def _filter_matches_with_llm(
    matches: list[AnalyticsOutputMatch],
    request: AnalyticsSearchRequest,
    phase: str,
) -> list[AnalyticsOutputMatch]:
    if not _should_run_llm_filter(matches, request, phase):
        return matches

    client = _get_analytics_llm()
    if client is None:
        return matches

    prompt = get_analytics_prompt(
        _llm_query_text(request),
        _llm_candidate_payload(matches),
        phase=phase,
        brief_problem_statement=request.brief_problem_statement,
        system_requirements=request.system_requirements,
    )

    try:
        response = client.with_structured_output(AnalyticsLLMRelevanceSelection).invoke(
            [
                (
                    "system",
                    "You are a strict banking glossary relevance judge. Keep only attributes that directly answer the requested business attribute. Treat brief problem statement and system requirements as supporting context only.",
                ),
                ("human", prompt),
            ]
        )
        if hasattr(response, "model_dump"):
            response = AnalyticsLLMRelevanceSelection.model_validate(response.model_dump())
        elif isinstance(response, dict):
            response = AnalyticsLLMRelevanceSelection.model_validate(response)
        else:
            response = AnalyticsLLMRelevanceSelection.model_validate(response)
    except Exception as exc:  # pragma: no cover
        logger.warning("Analytics semantic LLM filter failed: %s", exc)
        return matches

    keep_reason_by_doc_id = {
        decision.doc_id: decision.reason.strip()
        for decision in response.decisions
        if decision.keep and decision.doc_id
    }
    semantic_score_by_doc_id = {
        decision.doc_id: llm_score
        for decision in response.decisions
        if decision.keep
        and decision.doc_id
        and (llm_score := _clamp_similarity_score(decision.semantic_score)) is not None
    }
    keep_doc_ids = {decision.doc_id for decision in response.decisions if decision.keep and decision.doc_id}
    if not keep_doc_ids:
        return []

    filtered: list[AnalyticsOutputMatch] = []
    for match in matches:
        if match.doc_id not in keep_doc_ids:
            continue
        if keep_reason_by_doc_id.get(match.doc_id, ""):
            base = match.justification[:-1] if match.justification.endswith(".") else match.justification
            match.justification = f"{base}; LLM context check confirmed relevance."
        # Store LLM relevance score in justification for transparency.
        # It must NOT overwrite semantic_score (FAISS cosine similarity).
        # The two signals are distinct:
        #   semantic_score  = FAISS cosine similarity → feeds phase_weight
        #   llm_score       = Gemini relevance judgment → gate only, not in formula
        if match.doc_id in semantic_score_by_doc_id and match.match_phase != "phase1_exact":
            llm_score = semantic_score_by_doc_id[match.doc_id]
            match.justification = (
                match.justification.rstrip()
                + f"\n  [LLM relevance check: {round(llm_score * 100, 1)}% — gate only, not in score]"
            )
        filtered.append(match)
    return filtered


def _find_phase3_matches(
    candidate_positions: list[tuple[int, GlossaryRecord]],
    profile: QueryProfile,
    query_attribute: str,
    query_description: str,
    region: str,
    semantic_scores: dict[int, float],
) -> list[AnalyticsOutputMatch]:
    matches: list[AnalyticsOutputMatch] = []
    ranked_positions = sorted(
        candidate_positions,
        key=lambda item: semantic_scores.get(item[0], 0.0),
        reverse=True,
    )
    for position, record in ranked_positions[:SEMANTIC_CANDIDATE_LIMIT]:
        semantic_score = semantic_scores.get(position, 0.0)
        if not _passes_relevance_checklist(
            profile=profile,
            record=record,
            phase="phase3_semantic",
            semantic_score=semantic_score,
        ):
            continue

        domain_overlap = _domain_overlap_count(profile, record)
        overlap_bonus = domain_overlap * DESCRIPTION_OVERLAP_BONUS
        description_alignment = _description_alignment(profile, record)
        phase_weight = _match_weight(
            match_phase="phase3_semantic",
            domain_overlap=domain_overlap,
            description_alignment=description_alignment,
            semantic_score=semantic_score,
        )
        region_bonus = REGION_METADATA_BONUS if region and record.region == region else 0.0
        raw_score, max_score, recommendation_score = _compute_recommendation_score(
            match_phase="phase3_semantic",
            phase_weight=phase_weight,
            layer=record.asset_category,
            region_bonus=region_bonus,
        )
        justification = _build_justification(
            record=record,
            match_phase="phase3_semantic",
            query_attribute=query_attribute,
            query_description=query_description,
            recommendation_score=recommendation_score,
            raw_score=raw_score,
            max_score=max_score,
            phase_weight=phase_weight,
            semantic_score=semantic_score,
            domain_overlap=domain_overlap,
            description_alignment=description_alignment,
            region_bonus=region_bonus,
        )
        matches.append(
            _build_match(
                record=record,
                match_phase="phase3_semantic",
                justification=justification,
                internal_rank=semantic_score + overlap_bonus + description_alignment,
                phase_weight=phase_weight,
                semantic_score=semantic_score,
                recommendation_score=recommendation_score,
            )
        )
    return _sort_matches(matches)


def _run_phase1(
    request: AnalyticsSearchRequest,
    candidate_records: list[GlossaryRecord],
) -> list[AnalyticsOutputMatch]:
    matches = _dedupe_matches_by_entity(
        _find_phase1_matches(
            candidate_records=candidate_records,
            profile=request.profile,
            query_attribute=request.attribute_name,
            query_description=request.attribute_description,
            region=request.region,
        )
    )
    return _filter_matches_with_llm(matches, request, "phase1_exact")


def _run_phase2(
    request: AnalyticsSearchRequest,
    candidate_records: list[GlossaryRecord],
) -> list[AnalyticsOutputMatch]:
    matches = _dedupe_matches_by_entity(
        _find_phase2_matches(
            candidate_records=candidate_records,
            profile=request.profile,
            query_attribute=request.attribute_name,
            query_description=request.attribute_description,
            region=request.region,
        )
    )
    return _filter_matches_with_llm(matches, request, "phase2_fuzzy")


def _run_phase3(
    request: AnalyticsSearchRequest,
    index: AnalyticsIndex,
    candidate_positions: list[tuple[int, GlossaryRecord]],
    semantic_scores: dict[int, float] | None = None,
) -> list[AnalyticsOutputMatch]:
    if semantic_scores is None:
        semantic_scores = _semantic_score_map(
            index,
            _build_query_text(request.attribute_name, request.attribute_description, ""),
        )
    matches = _find_phase3_matches(
        candidate_positions=candidate_positions,
        profile=request.profile,
        query_attribute=request.attribute_name,
        query_description=request.attribute_description,
        region=request.region,
        semantic_scores=semantic_scores,
    )
    matches = _strict_semantic_attribute_filter(matches, request.profile)
    matches = _filter_matches_with_llm(matches, request, "phase3_semantic")
    return _dedupe_matches_by_entity(matches)[:MAX_PHASE3_MATCHES]


def _build_cda_llm_suggestion(
    request: AnalyticsSearchRequest,
    cda_record: GlossaryRecord,
    gda_mda_records: list[GlossaryRecord],
) -> str:
    """
    Calls Gemini to reason from the requirement definition alone and identify
    which existing GDA/MDA attributes can be used to derive the target.
    CDA confirms the attribute exists at source but is NOT used as the derivation path.
    Falls back to rule-based suggestion if LLM is unavailable.
    """
    client = _get_analytics_llm()

    # Build GDA/MDA attribute catalogue — this is what Gemini reasons over
    available_attrs = "\n".join(
        f"  [{r.asset_category}] {r.asset_name}.{r.attribute_name} | {r.attribute_description}"
        for r in gda_mda_records[:40]
        if r.attribute_description
    ) or "  (No GDA/MDA attributes available)"

    target_col = _normalize_name(request.attribute_name)

    prompt = f"""You are a senior data engineer on a banking data platform (GDA/MDA/CDA layers).

A business analyst requires a new derived attribute:
  Name:       {request.attribute_name}
  Definition: {request.attribute_description or "Not provided"}

This attribute does NOT yet exist in GDA or MDA. Your job is to reason from the definition
and identify which existing GDA/MDA attributes below can be combined or transformed to produce it.
Do NOT reference CDA in your answer — the derivation must come from GDA or MDA only.

Available GDA/MDA attributes (layer | table.attribute | description):
{available_attrs}

Instructions:
1. Read the definition carefully. Identify the key business concept (e.g. banding, grouping, 
   amount thresholds, status classification, etc.).
2. Select the most relevant GDA/MDA attribute(s) whose definition aligns with deriving this output.
3. Explain in plain English (3-5 sentences) exactly how to derive '{request.attribute_name}' 
   from those attributes — include any CASE/WHEN banding logic, joins, or calculations needed.
4. Write a concrete SQL query that produces '{target_col}' as the output column,
   sourced entirely from GDA/MDA tables. Use realistic CASE/WHEN if banding is involved.

Respond in EXACTLY this format (no extra text):
REASONING:
<which GDA/MDA attributes you selected and why, 2-3 sentences>

TRANSFORMATION:
<plain English derivation logic, 3-5 sentences>

SQL:
<sql query only>"""

    if client is not None:
        try:
            response = client.invoke([
                (
                    "system",
                    "You are a strict banking data engineering assistant. "
                    "Always derive attributes from GDA/MDA only. "
                    "Never suggest reading directly from CDA or raw source. "
                    "Always include CASE/WHEN logic when banding or classification is implied by the definition.",
                ),
                ("human", prompt),
            ])
            raw = response.content if hasattr(response, "content") else str(response)
            return raw.strip()
        except Exception as exc:
            logger.warning("CDA LLM suggestion failed: %s", exc)

    # ── Rule-based fallback (LLM unavailable) ────────────────────────────
    # Detect derivation pattern from the definition, then pick the best
    # GDA/MDA source attribute and produce an appropriate SQL template.

    definition_lower = (request.attribute_description or "").lower()
    target_col = _normalize_name(request.attribute_name)

    # ── Pattern detection ─────────────────────────────────────────────────
    PATTERN_KEYWORDS: list[tuple[str, list[str]]] = [
        ("band_or_group",  ["band", "group", "tier", "bucket", "segment", "range", "bracket"]),
        ("status_or_code", ["status", "code", "flag", "indicator", "category", "classification", "type"]),
        ("amount_or_value", ["amount", "balance", "outstanding", "exposure", "value", "limit", "principal"]),
        ("date_or_period",  ["date", "period", "month", "year", "day", "timestamp", "quarter"]),
        ("rate_or_ratio",   ["rate", "ratio", "percent", "percentage", "proportion"]),
        ("count",           ["count", "number of", "quantity", "total number"]),
        ("name_or_label",   ["name", "label", "description", "title"]),
    ]

    detected_pattern = "generic"
    for pattern_name, keywords in PATTERN_KEYWORDS:
        if any(kw in definition_lower for kw in keywords):
            detected_pattern = pattern_name
            break

    # ── Source attribute selection: score GDA/MDA records by definition overlap ──
    def _overlap_score(record: GlossaryRecord) -> int:
        desc = (record.attribute_description or "").lower()
        return sum(1 for word in definition_lower.split() if len(word) > 3 and word in desc)

    scored = sorted(gda_mda_records, key=_overlap_score, reverse=True)
    best_attr = scored[0] if scored else None
    source_ref = (
        f"{best_attr.asset_name}.{best_attr.attribute_name}"
        if best_attr else "GDA.<source_table>.<source_attribute>"
    )
    source_desc = (best_attr.attribute_description or "") if best_attr else ""
    source_table = source_ref.rsplit(".", 1)[0]

    # ── SQL template by pattern ───────────────────────────────────────────
    if detected_pattern == "band_or_group":
        sql_body = (
            f"    CASE\n"
            f"        WHEN {source_ref} < <threshold_1>  THEN '<band_label_1>'\n"
            f"        WHEN {source_ref} < <threshold_2>  THEN '<band_label_2>'\n"
            f"        WHEN {source_ref} < <threshold_3>  THEN '<band_label_3>'\n"
            f"        ELSE                                    '<band_label_4>'\n"
            f"    END AS {target_col}"
        )
        transform_hint = (
            f"Apply threshold-based CASE/WHEN banding to '{source_ref}'. "
            f"Band thresholds and labels must be confirmed with the business "
            f"before implementation."
        )

    elif detected_pattern == "status_or_code":
        sql_body = (
            f"    CASE {source_ref}\n"
            f"        WHEN '<raw_value_1>' THEN '<mapped_code_1>'\n"
            f"        WHEN '<raw_value_2>' THEN '<mapped_code_2>'\n"
            f"        ELSE '<default_code>'\n"
            f"    END AS {target_col}"
        )
        transform_hint = (
            f"Map raw values of '{source_ref}' to standardised codes/statuses. "
            f"The value mapping must be confirmed with the business or a reference table."
        )

    elif detected_pattern == "amount_or_value":
        sql_body = (
            f"    {source_ref} AS {target_col}"
        )
        transform_hint = (
            f"Directly derive '{target_col}' from '{source_ref}', "
            f"which represents {source_desc or 'the underlying monetary value'}. "
            f"Apply any currency conversion or rounding as required."
        )

    elif detected_pattern == "date_or_period":
        sql_body = (
            f"    CAST({source_ref} AS DATE) AS {target_col}"
        )
        transform_hint = (
            f"Cast or extract the date/period component from '{source_ref}'. "
            f"Confirm the date format and granularity (day/month/year) with the business."
        )

    elif detected_pattern == "rate_or_ratio":
        sql_body = (
            f"    ROUND({source_ref} * 100.0, 4) AS {target_col}  -- adjust formula as needed"
        )
        transform_hint = (
            f"Derive the rate or ratio from '{source_ref}'. "
            f"Confirm whether the output should be expressed as a decimal or percentage."
        )

    elif detected_pattern == "count":
        sql_body = (
            f"    COUNT({source_ref}) AS {target_col}"
        )
        transform_hint = (
            f"Count occurrences of '{source_ref}' grouped by the relevant entity key. "
            f"Confirm the grain and grouping with the business."
        )

    else:  # generic
        sql_body = (
            f"    {source_ref} AS {target_col}  -- review and adjust derivation"
        )
        transform_hint = (
            f"Derive '{target_col}' from '{source_ref}' "
            f"({source_desc or 'see attribute description'}). "
            f"Review the exact transformation logic with the business."
        )

    reasoning = (
        f"The definition '{request.attribute_description}' suggests a "
        f"'{detected_pattern.replace('_', ' ')}' derivation pattern. "
        f"The closest GDA/MDA attribute is '{source_ref}' "
        f"('{source_desc}'), selected by definition overlap scoring."
    )

    transformation = (
        f"'{request.attribute_name}' does not exist in GDA or MDA. "
        f"{transform_hint} "
        f"A GDA enhancement request should be raised to formalise this attribute "
        f"once the derivation logic is confirmed."
    )

    sql = (
        f"-- Suggested derivation for: {request.attribute_name}\n"
        f"-- Pattern detected: {detected_pattern}\n"
        f"-- Source: GDA/MDA only (CDA not used in derivation)\n"
        f"-- NOTE: Replace <placeholder> values with confirmed business thresholds/mappings\n"
        f"SELECT\n"
        f"{sql_body}\n"
        f"FROM {source_table}\n"
        f"WHERE {source_ref} IS NOT NULL;"
    )

    return f"REASONING:\n{reasoning}\n\nTRANSFORMATION:\n{transformation}\n\nSQL:\n{sql}"


def _build_cda_suggestion_match(
    request: AnalyticsSearchRequest,
    cda_record: GlossaryRecord,
    gda_mda_records: list[GlossaryRecord],
) -> AnalyticsOutputMatch:
    """
    Builds a synthetic AnalyticsOutputMatch for the CDA suggestion path.
    This is NOT a real match — it's a suggestion card shown to the user.
    """
    suggestion_text = _build_cda_llm_suggestion(request, cda_record, gda_mda_records)
    return AnalyticsOutputMatch(
        doc_id=cda_record.doc_id,
        asset_category="CDA",
        asset_name=cda_record.asset_name,
        asset_attribute=cda_record.asset_attribute,
        entity_name=cda_record.entity_name,
        entity_description=cda_record.entity_description,
        attribute_name=cda_record.attribute_name,
        attribute_description=cda_record.attribute_description,
        source_description=cda_record.source_description,
        lineage_assets=cda_record.lineage_assets,
        join_keys=cda_record.join_keys,
        region=cda_record.region,
        match_phase="phase_cda_suggestion",
        phase_weight=0.0,         # not scored — suggestion only
        fuzzy_score=0.0,
        semantic_score=0.0,
        justification=suggestion_text,
        relevance_score=0.0,
    )


def _run_matching_pipeline(
    request: AnalyticsSearchRequest,
    index: AnalyticsIndex,
    candidate_positions: list[tuple[int, GlossaryRecord]],
    candidate_records: list[GlossaryRecord],
) -> tuple[str, list[AnalyticsOutputMatch]]:
    # CDA is excluded from all competitive matching — GDA and MDA only
    gda_records = _records_for_layer(candidate_records, "GDA")
    mda_records = _records_for_layer(candidate_records, "MDA")
    gda_positions = _positions_for_layer(candidate_positions, "GDA")
    mda_positions = _positions_for_layer(candidate_positions, "MDA")
    gda_mda_positions = [p for p in candidate_positions if p[1].asset_category in ("GDA", "MDA")]

    exact_gda_matches = _run_phase1(request, gda_records)
    if exact_gda_matches:
        return "phase1_exact", _rank_candidate_matches(request, exact_gda_matches)

    semantic_scores = _semantic_score_map(
        index,
        _build_query_text(request.attribute_name, request.attribute_description, ""),
    )
    semantic_scores_by_doc_id = _semantic_scores_by_doc_id(candidate_positions, semantic_scores)

    exact_mda_matches = _run_phase1(request, mda_records)
    fuzzy_gda_matches = _apply_semantic_scores_to_matches(
        _run_phase2(request, gda_records),
        semantic_scores_by_doc_id,
    )
    if fuzzy_gda_matches:
        return "phase2_fuzzy", _rank_candidate_matches(
            request,
            exact_mda_matches,
            fuzzy_gda_matches,
        )

    semantic_gda_matches = _run_phase3(request, index, gda_positions, semantic_scores)
    if semantic_gda_matches:
        return "phase3_semantic", _rank_candidate_matches(
            request,
            exact_mda_matches,
            semantic_gda_matches,
        )

    if exact_mda_matches:
        return "phase1_exact_mda_only", _rank_candidate_matches(request, exact_mda_matches)

    fuzzy_mda_matches = _apply_semantic_scores_to_matches(
        _run_phase2(request, mda_records),
        semantic_scores_by_doc_id,
    )
    if fuzzy_mda_matches:
        return "phase2_fuzzy_mda_only", _rank_candidate_matches(request, fuzzy_mda_matches)

    semantic_mda_matches = _run_phase3(request, index, mda_positions, semantic_scores)
    if semantic_mda_matches:
        return "phase3_semantic_mda_only", _rank_candidate_matches(request, semantic_mda_matches)

    # ── Last resort: CDA lookup ───────────────────────────────────────────
    # CDA is never scored or surfaced as a match — only checked to confirm
    # the attribute exists at source so we can generate a derivation suggestion.
    cda_records = _records_for_layer(candidate_records, "CDA")
    cda_exact = _find_phase1_matches(
        candidate_records=cda_records,
        profile=request.profile,
        query_attribute=request.attribute_name,
        query_description=request.attribute_description,
        region=request.region,
    )
    if not cda_exact:
        cda_fuzzy = _find_phase2_matches(
            candidate_records=cda_records,
            profile=request.profile,
            query_attribute=request.attribute_name,
            query_description=request.attribute_description,
            region=request.region,
        )
        cda_hits = cda_fuzzy
    else:
        cda_hits = cda_exact

    if cda_hits:
        # Build LLM-powered suggestion using CDA context + GDA/MDA existing attributes
        gda_mda_records = gda_records + mda_records
        suggestion_match = _build_cda_suggestion_match(request, cda_hits[0], gda_mda_records)
        return "phase_cda_suggestion", [suggestion_match]

    return "", []




def _build_selected_details(
    matches: list[AnalyticsOutputMatch],
    selected_value_stream: str,
) -> dict[str, Any]:
    """
    Build the selected_details block for the response.

    Key behaviour: if the user has explicitly chosen a stream, that stream's
    layer (MDA or GDA) drives the entire block — even when the other layer
    has matches in the list.  Without a selection the default is GDA-first.
    """
    gda_matches = [m for m in matches if m.asset_category == "GDA" and m.asset_name]
    mda_matches = [m for m in matches if m.asset_category == "MDA" and m.asset_name]

    # Determine which layer the user selected (if any).
    # Try resolving against GDA first, then MDA.
    user_picked_gda = _resolve_selected_asset_name(gda_matches, selected_value_stream, "GDA") if gda_matches else ""
    user_picked_mda = _resolve_selected_asset_name(mda_matches, selected_value_stream, "MDA") if mda_matches else ""

    # If user explicitly selected an MDA stream, serve MDA details.
    if user_picked_mda and not user_picked_gda:
        mda_value_stream_details: dict[str, list[dict[str, Any]]] = {}
        for match in mda_matches:
            mda_value_stream_details.setdefault(match.asset_name, []).append(_slim_match_payload(match))
        mda_value_streams = list(mda_value_stream_details)
        selected_details: dict[str, Any] = {
            "preferred_layer": "MDA",
            "mda_value_streams": mda_value_streams,
            "mda_value_stream_details": mda_value_stream_details,
            "selected_mda_value_stream": user_picked_mda,
            "selected_mda_details": mda_value_stream_details.get(user_picked_mda, []),
        }
        return selected_details

    # Default: GDA-first (auto-select if only one GDA stream).
    if gda_matches:
        gda_value_stream_details: dict[str, list[dict[str, Any]]] = {}
        for match in gda_matches:
            gda_value_stream_details.setdefault(match.asset_name, []).append(_slim_match_payload(match))
        gda_value_streams = list(gda_value_stream_details)
        selected_gda = user_picked_gda or (gda_value_streams[0] if len(gda_value_streams) == 1 else "")
        selected_details = {
            "preferred_layer": "GDA",
            "gda_value_streams": gda_value_streams,
            "gda_value_stream_details": gda_value_stream_details,
        }
        if selected_gda:
            selected_details["selected_gda_value_stream"] = selected_gda
            selected_details["selected_gda_details"] = gda_value_stream_details.get(selected_gda, [])
        return selected_details

    # MDA-only fallback (no GDA at all).
    if not mda_matches:
        return {
            "preferred_layer": "",
            "selection_reason": "No data is found at MDA or GDA level.",
            "gda_value_streams": [],
            "mda_value_streams": [],
        }
    mda_value_stream_details = {}
    for match in mda_matches:
        mda_value_stream_details.setdefault(match.asset_name, []).append(_slim_match_payload(match))
    mda_value_streams = list(mda_value_stream_details)
    selected_mda = user_picked_mda or (mda_value_streams[0] if mda_value_streams else "")
    selected_details = {
        "preferred_layer": "MDA",
        "mda_value_streams": mda_value_streams,
        "mda_value_stream_details": mda_value_stream_details,
    }
    if selected_mda:
        selected_details["selected_mda_value_stream"] = selected_mda
        selected_details["selected_mda_details"] = mda_value_stream_details.get(selected_mda, [])
    return selected_details


def _build_response(
    request: AnalyticsSearchRequest,
    matches: list[AnalyticsOutputMatch],
    phase_used: str,
    metadata: AnalyticsRetrievalMetadata,
) -> AnalyticsResponse:
    metadata.phase_used = phase_used
    metadata.returned_matches = len(matches)
    gda_asset_names = _gda_asset_names(matches)

    # CDA suggestion path — treat as no_match with a derivation suggestion, not a real match
    if phase_used == "phase_cda_suggestion":
        cda_match = matches[0] if matches else None
        return AnalyticsResponse(
            original_query=request.original_query,
            requested_attribute_name=request.attribute_name,
            requested_attribute_description=request.attribute_description,
            requested_region=request.region,
            status="cda_suggestion",
            answer=(
                f"'{request.attribute_name}' was not found in GDA or MDA. "
                f"However, it exists in CDA (raw layer) as "
                f"'{cda_match.asset_name}.{cda_match.attribute_name}' "
                f"and can be derived. See the transformation suggestion below."
                if cda_match else
                f"'{request.attribute_name}' was not found in GDA or MDA."
            ),
            match_phase="phase_cda_suggestion",
            human_in_loop_required=True,
            human_in_loop_prompt=(
                "This attribute exists only in CDA (raw layer). "
                "Review the suggested transformation and SQL below, then confirm or modify "
                "before raising a GDA enhancement request."
            ),
            human_selection_options=[],
            selected_details={
                "preferred_layer": "CDA",
                "cda_suggestion": cda_match.justification if cda_match else "",
                "cda_attribute": cda_match.attribute_name if cda_match else "",
                "cda_source": cda_match.asset_name if cda_match else "",
            },
            relevant_matches=[_slim_match(cda_match)] if cda_match else [],
            layer_summary=_build_layer_summary(matches),
            retrieval_metadata=metadata,
        )

    gda_found_via_non_exact = any(
        match.asset_category == "GDA" and match.match_phase != "phase1_exact"
        for match in matches
    )
    human_in_loop_required = (
        (len(gda_asset_names) > 1 and not request.selected_asset_name)
        or (gda_found_via_non_exact and not request.selected_asset_name)
        or phase_used in ("phase1_exact_mda_only", "phase2_fuzzy_mda_only", "phase3_semantic_mda_only")
    )
    return AnalyticsResponse(
        original_query=request.original_query,
        requested_attribute_name=request.attribute_name,
        requested_attribute_description=request.attribute_description,
        requested_region=request.region,
        status="requires_human_selection" if human_in_loop_required else "matched" if matches else "no_match",
        answer=_build_answer(
            request.attribute_name,
            request.region,
            phase_used,
            len(matches),
            gda_asset_names,
            request.selected_asset_name,
        ),
        match_phase=phase_used if matches else "",
        human_in_loop_required=human_in_loop_required,
        human_in_loop_prompt=_build_human_selection_prompt(gda_asset_names) if human_in_loop_required else "",
        human_selection_options=gda_asset_names if human_in_loop_required else [],
        selected_details=_build_selected_details(matches, request.selected_asset_name),
        relevant_matches=[_slim_match(match) for match in matches],
        layer_summary=_build_layer_summary(matches),
        retrieval_metadata=metadata,
    )


def _build_human_selection_prompt(gda_value_streams: list[str]) -> str:
    if len(gda_value_streams) <= 1:
        return ""
    return (
        "Multiple GDA value streams are available: "
        f"{', '.join(gda_value_streams)}. Please select the GDA value stream to use."
    )


def _build_answer(
    attribute_name: str,
    region: str,
    phase_used: str,
    match_count: int,
    gda_asset_names: list[str] | None = None,
    selected_asset_name: str = "",
) -> str:
    if match_count <= 0:
        if region:
            return f"No relevant glossary attribute was found for the request in region '{region}'."
        return "No relevant glossary attribute was found for the requested search."

    gda_asset_names = gda_asset_names or []
    region_text = f" in region {region}" if region else ""
    if len(gda_asset_names) > 1 and not selected_asset_name:
        return (
            f"Found {match_count} relevant match(es) for '{attribute_name}'{region_text} "
            f"using {PHASE_LABELS.get(phase_used, 'the matching pipeline')}. "
            f"Human selection is required between GDA value streams: {', '.join(gda_asset_names)}."
        )
    if selected_asset_name:
        return (
            f"Found {match_count} relevant match(es) for '{attribute_name}'{region_text} "
            f"from selected value stream {selected_asset_name} using "
            f"{PHASE_LABELS.get(phase_used, 'the matching pipeline')}."
        )
    return (
        f"Found {match_count} relevant match(es) for '{attribute_name}'{region_text} "
        f"using {PHASE_LABELS.get(phase_used, 'the matching pipeline')}."
    )


def search_analytics(
    attribute_name: str,
    attribute_description: str = "",
    region: str = "",
    selected_asset_name: str = "",
    brief_problem_statement: str = "",
    system_requirements: str = "",
) -> AnalyticsResponse:
    request = _build_search_request(
        attribute_name,
        attribute_description,
        region,
        selected_asset_name,
        brief_problem_statement,
        system_requirements,
    )
    index = _get_analytics_index()
    candidate_positions, candidate_records = _candidate_records_for_region(index, request.region)
    metadata = _build_retrieval_metadata(index, candidate_records)

    if not candidate_records:
        return _build_response(request, [], "", metadata)

    phase_used, relevant_matches = _run_matching_pipeline(
        request=request,
        index=index,
        candidate_positions=candidate_positions,
        candidate_records=candidate_records,
    )
    relevant_matches = enrich_gda_matches_with_lineage(relevant_matches)
    if request.selected_asset_name:
        request.selected_asset_name = _resolve_selected_asset_name_any(
            relevant_matches,
            request.selected_asset_name,
        )
    relevant_matches = _filter_matches_for_selected_asset(
        relevant_matches,
        request.selected_asset_name,
    )
    return _build_response(request, relevant_matches, phase_used, metadata)


def _extract_batch_query(item: dict[str, Any] | Any) -> tuple[str, str, str, str, str, str]:
    if hasattr(item, "attribute_name"):
        return (
            _safe_text(item.attribute_name),
            _safe_text(getattr(item, "attribute_description", "")),
            _safe_text(getattr(item, "region", "")),
            _safe_text(getattr(item, "selected_value_stream", "")) or _safe_text(getattr(item, "selected_asset_name", "")),
            _safe_text(getattr(item, "brief_problem_statement", "")),
            _safe_text(getattr(item, "system_requirements", "")),
        )
    return (
        _safe_text(item.get("attribute_name")),
        _safe_text(item.get("attribute_description")),
        _safe_text(item.get("region")),
        _safe_text(item.get("selected_value_stream")) or _safe_text(item.get("selected_asset_name")),
        _safe_text(item.get("brief_problem_statement")),
        _safe_text(item.get("system_requirements")),
    )


def _response_payload(response: AnalyticsResponse) -> dict[str, Any]:
    return response.model_dump(mode="json", by_alias=True, exclude_none=True, exclude_defaults=True)


def search_analytics_batch(queries: list[dict[str, Any]] | list[Any]) -> dict[str, Any]:
    if not queries:
        raise ValueError("At least one analytics request is required for batch search.")

    results = []
    for item in queries:
        (
            attribute_name,
            attribute_description,
            region,
            selected_asset_name,
            brief_problem_statement,
            system_requirements,
        ) = _extract_batch_query(item)
        output = search_analytics(
            attribute_name=attribute_name,
            attribute_description=attribute_description,
            region=region,
            selected_asset_name=selected_asset_name,
            brief_problem_statement=brief_problem_statement,
            system_requirements=system_requirements,
        )
        results.append(
            {
                "query": output.original_query,
                "output": _response_payload(output),
            }
        )

    payload = {
        "total_queries": len(results),
        "output_json_path": str(ANALYTICS_QUERY_OUTPUT_PATH),
        "results": results,
    }
    ANALYTICS_QUERY_OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return payload


def record_analytics_query_result(response: AnalyticsResponse) -> str:
    existing: list[dict[str, Any]]
    try:
        raw = json.loads(ANALYTICS_QUERY_OUTPUT_PATH.read_text(encoding="utf-8"))
        existing = raw if isinstance(raw, list) else []
    except FileNotFoundError:
        existing = []
    except json.JSONDecodeError:
        existing = []

    existing.append(_response_payload(response))
    ANALYTICS_QUERY_OUTPUT_PATH.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(ANALYTICS_QUERY_OUTPUT_PATH)