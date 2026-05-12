from __future__ import annotations

import logging
import re
from typing import Dict, List

import numpy as np

try:
    from core_banking_glossary_knowledge_base import CORE_BANKING_GLOSSARY_KNOWLEDGE_BASE
    from config import rag_embeddings_enabled
    from loan_glossary_knowledge_base import LOAN_GLOSSARY_KNOWLEDGE_BASE
except ImportError:  # pragma: no cover - supports package-style imports
    from .core_banking_glossary_knowledge_base import CORE_BANKING_GLOSSARY_KNOWLEDGE_BASE
    from .config import rag_embeddings_enabled
    from .loan_glossary_knowledge_base import LOAN_GLOSSARY_KNOWLEDGE_BASE

try:
    import faiss
except ImportError:  
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - demo can still run with keyword fallback
    SentenceTransformer = None


#editd by mani
KNOWLEDGE_BASES: Dict[str, List[str]] = {
    "loan": LOAN_GLOSSARY_KNOWLEDGE_BASE,
    "core_banking": CORE_BANKING_GLOSSARY_KNOWLEDGE_BASE,
}

#editd by mani
LOAN_DOMAIN_KEYWORDS = {
    "loan",
    "loan_account",
    "facility",
    "credit risk",
    "credit_risk",
    "credit_assessment",
    "risk_rating",
    "collateral",
    "guarantor",
    "loan_monitoring",
    "default_event",
    "recovery_event",
    "provision",
    "cibil",
    "dpd",
}

logger = logging.getLogger(__name__)

_model = None
_vector_indexes: Dict[str, object] = {}
_vector_embeddings: Dict[str, np.ndarray] = {}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower().replace("_", " "))


#editd by mani
def _canonical_name_from_entry(item: str) -> str:
    patterns = [
        r"Canonical table:\s*([A-Z0-9_]+)",
        r"Canonical ER entity:\s*([A-Z0-9_]+)",
        r"Entity profile:\s*([A-Z0-9_]+)",
        r"Table summary:\s*([A-Z0-9_]+)",
        r"Relationship rule:\s*([A-Z0-9_]+)\s+to\s+([A-Z0-9_]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, item)
        if not match:
            continue
        if len(match.groups()) == 1:
            return match.group(1)
        return f"{match.group(1)} {match.group(2)}"
    return ""


#editd by mani
def _select_knowledge_base_name(query: str) -> str:
    normalized_query = query.lower().replace("-", " ").replace("_", " ")
    for keyword in LOAN_DOMAIN_KEYWORDS:
        normalized_keyword = keyword.replace("_", " ")
        if normalized_keyword in normalized_query:
            return "loan"
    return "core_banking"


#editd by mani
def _get_knowledge_base(query: str) -> List[str]:
    return KNOWLEDGE_BASES[_select_knowledge_base_name(query)]


#editd by mani
def _ensure_model():
    global _model
    if not rag_embeddings_enabled():
        return None
    if SentenceTransformer is None or faiss is None:
        return None
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


#editd by mani
def _build_vector_store_for_base(base_name: str) -> None:
    if base_name in _vector_indexes:
        return

    model = _ensure_model()
    if model is None:
        return

    knowledge_base = KNOWLEDGE_BASES[base_name]
    embeddings = np.array(model.encode(knowledge_base))
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    _vector_embeddings[base_name] = embeddings
    _vector_indexes[base_name] = index


#editd by mani
def warm_rag() -> None:
    try:
        for base_name in KNOWLEDGE_BASES:
            _build_vector_store_for_base(base_name)
    except Exception as exc:  # pragma: no cover - app can still run with keyword fallback
        logger.warning("RAG warmup skipped: %s", exc)


#editd by mani
def _keyword_fallback(query: str, k: int, knowledge_base: List[str]) -> List[str]:
    query_terms = set(_tokenize(query))
    scored = []
    for item in knowledge_base:
        item_terms = set(_tokenize(item))
        overlap = len(query_terms.intersection(item_terms))
        scored.append((overlap, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:k]]


#editd by mani
def _explicit_entity_matches(query: str, knowledge_base: List[str]) -> List[str]:
    normalized_query = " " + re.sub(r"[^a-z0-9]+", " ", query.lower().replace("_", " ")) + " "
    matches = []
    for item in knowledge_base:
        canonical_name = _canonical_name_from_entry(item)
        if not canonical_name:
            continue
        normalized_name = re.sub(r"[^a-z0-9]+", " ", canonical_name.lower().replace("_", " "))
        if f" {normalized_name} " in normalized_query and item not in matches:
            matches.append(item)
    return matches


def get_relevant_context(query: str, k: int = 3) -> str:
    base_name = _select_knowledge_base_name(query)
    knowledge_base = KNOWLEDGE_BASES[base_name]
    _build_vector_store_for_base(base_name)

    index = _vector_indexes.get(base_name)
    model = _model

    if index is not None and model is not None:
        query_embedding = np.array(model.encode([query]))
        _, indices = index.search(query_embedding, k)
        semantic_results = [knowledge_base[i] for i in indices[0]]
        keyword_results = _keyword_fallback(query, k, knowledge_base)
        explicit_results = _explicit_entity_matches(query, knowledge_base)
        results = []
        for item in explicit_results + keyword_results + semantic_results:
            if item not in results:
                results.append(item)
        results = results[: max(k, len(explicit_results))]
    else:
        explicit_results = _explicit_entity_matches(query, knowledge_base)
        results = []
        for item in explicit_results + _keyword_fallback(query, k, knowledge_base):
            if item not in results:
                results.append(item)
        results = results[: max(k, len(explicit_results))]

    return "\n".join(results)
