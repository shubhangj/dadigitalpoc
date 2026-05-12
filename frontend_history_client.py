from __future__ import annotations

from typing import Any, Dict

import requests


class BackendHistoryClient:
    """Small HTTP client for project-history endpoints on the FastAPI backend."""

    def __init__(self, base_url: str, timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_store(self) -> Dict[str, Any] | None:
        return self._request("GET", "/projects/store")

    def put_store(self, store: Dict[str, Any]) -> Dict[str, Any] | None:
        return self._request("PUT", "/projects/store", store)

    def get_project(self, project_id: str) -> Dict[str, Any] | None:
        return self._request("GET", f"/projects/{project_id}")

    def put_project(self, project: Dict[str, Any]) -> Dict[str, Any] | None:
        project_id = project.get("project_id")
        if not project_id:
            return None
        return self._request("PUT", f"/projects/{project_id}", project)

    def _request(
        self,
        method: str,
        path: str,
        payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any] | None:
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                json=payload,
                timeout=self.timeout_seconds,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
        except Exception:
            return None

        return data if isinstance(data, dict) else None
