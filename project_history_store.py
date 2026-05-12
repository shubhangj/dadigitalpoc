from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4


DEFAULT_PROJECT_REPOSITORY_PATH = Path(__file__).with_name("project_repository")
# POC mode: always use the app-local folder and ignore old Render disk env vars.
PROJECT_REPOSITORY_PATH = DEFAULT_PROJECT_REPOSITORY_PATH
PROJECT_STORE_FILE = PROJECT_REPOSITORY_PATH / "history.json"


def _current_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ensure_project_repository() -> None:
    PROJECT_REPOSITORY_PATH.mkdir(parents=True, exist_ok=True)


def _normalize_project(project: Dict[str, Any]) -> Dict[str, Any]:
    timestamp = _current_timestamp()
    if not project.get("project_id"):
        project["project_id"] = uuid4().hex
    if not project.get("project_name"):
        project["project_name"] = project.get("name") or f"Project {timestamp}"
    if not project.get("created_at"):
        project["created_at"] = project.get("updated_at") or timestamp
    if not project.get("updated_at"):
        project["updated_at"] = timestamp
    if not isinstance(project.get("chat_history"), list):
        project["chat_history"] = []
    if not isinstance(project.get("state"), dict):
        project["state"] = {}
    if not isinstance(project.get("diagram_json"), dict):
        project["diagram_json"] = {}
    return project


def read_project_store() -> Dict[str, Any]:
    """Read the full history file, returning an empty store when it is missing."""
    _ensure_project_repository()
    if not PROJECT_STORE_FILE.exists():
        return {"version": 2, "updated_at": _current_timestamp(), "projects": []}

    try:
        store = json.loads(PROJECT_STORE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 2, "updated_at": _current_timestamp(), "projects": []}

    if not isinstance(store, dict):
        store = {}

    projects = store.get("projects")
    if not isinstance(projects, list):
        projects = []

    normalized_projects = [
        _normalize_project(project)
        for project in projects
        if isinstance(project, dict)
    ]
    return {
        "version": store.get("version", 2),
        "updated_at": store.get("updated_at") or _current_timestamp(),
        "projects": normalized_projects,
    }


def write_project_store(store: Dict[str, Any]) -> Dict[str, Any]:
    """Replace the full history file and return the normalized store."""
    _ensure_project_repository()
    projects = store.get("projects") if isinstance(store, dict) else []
    if not isinstance(projects, list):
        projects = []

    normalized_store = {
        "version": store.get("version", 2) if isinstance(store, dict) else 2,
        "updated_at": _current_timestamp(),
        "projects": [
            _normalize_project(project)
            for project in projects
            if isinstance(project, dict)
        ],
    }
    PROJECT_STORE_FILE.write_text(
        json.dumps(normalized_store, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return normalized_store


def read_project(project_id: str) -> Dict[str, Any] | None:
    """Return one project by id from the history store."""
    store = read_project_store()
    for project in store.get("projects", []):
        if project.get("project_id") == project_id:
            return project
    return None


def write_project(project: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update one project in the history store."""
    normalized_project = _normalize_project(dict(project))
    store = read_project_store()
    projects = store.setdefault("projects", [])

    for index, existing_project in enumerate(projects):
        if existing_project.get("project_id") == normalized_project["project_id"]:
            projects[index] = normalized_project
            break
    else:
        projects.append(normalized_project)

    write_project_store(store)
    return normalized_project
