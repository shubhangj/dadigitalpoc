from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - app can still run if env vars are already exported
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


#editd by mani
def get_gemini_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


#editd by mani
def get_gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-pro")


def get_analytics_glossary_json_path() -> str | None:
    return os.getenv("ANALYTICS_GLOSSARY_JSON_PATH")


def get_analytics_glossary_xlsx_path() -> str | None:
    return os.getenv("ANALYTICS_GLOSSARY_XLSX_PATH")


def warm_models_on_startup_enabled() -> bool:
    return _env_flag("WARM_MODELS_ON_STARTUP", False)


def analytics_embeddings_enabled() -> bool:
    return _env_flag("ANALYTICS_EMBEDDINGS_ENABLED", False)


def rag_embeddings_enabled() -> bool:
    return _env_flag("RAG_EMBEDDINGS_ENABLED", False)
