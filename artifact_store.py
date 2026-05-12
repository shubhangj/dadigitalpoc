from __future__ import annotations

from typing import Dict
from uuid import uuid4

try:
    from schemas import ConceptualModel, LogicalModel, PhysicalModel
except ImportError:  # pragma: no cover - supports package-style imports
    from .schemas import ConceptualModel, LogicalModel, PhysicalModel


_CONCEPTUAL_ARTIFACTS: Dict[str, ConceptualModel] = {}
_CONCEPTUAL_ARTIFACT_STATUS: Dict[str, str] = {}
_LOGICAL_ARTIFACTS: Dict[str, LogicalModel] = {}
_PHYSICAL_ARTIFACTS: Dict[str, PhysicalModel] = {}


def save_conceptual_artifact(conceptual_model: ConceptualModel, status: str = "draft") -> str:
    artifact_id = str(uuid4())
    _CONCEPTUAL_ARTIFACTS[artifact_id] = conceptual_model
    _CONCEPTUAL_ARTIFACT_STATUS[artifact_id] = status
    return artifact_id


def get_conceptual_artifact(artifact_id: str) -> ConceptualModel | None:
    return _CONCEPTUAL_ARTIFACTS.get(artifact_id)


#editd by mani
def update_conceptual_artifact(artifact_id: str, conceptual_model: ConceptualModel) -> None:
    _CONCEPTUAL_ARTIFACTS[artifact_id] = conceptual_model


#editd by mani
def get_conceptual_artifact_status(artifact_id: str) -> str | None:
    return _CONCEPTUAL_ARTIFACT_STATUS.get(artifact_id)


#editd by mani
def set_conceptual_artifact_status(artifact_id: str, status: str) -> None:
    if artifact_id in _CONCEPTUAL_ARTIFACTS:
        _CONCEPTUAL_ARTIFACT_STATUS[artifact_id] = status


def save_logical_artifact(logical_model: LogicalModel) -> str:
    artifact_id = str(uuid4())
    _LOGICAL_ARTIFACTS[artifact_id] = logical_model
    return artifact_id


def get_logical_artifact(artifact_id: str) -> LogicalModel | None:
    return _LOGICAL_ARTIFACTS.get(artifact_id)


def save_physical_artifact(physical_model: PhysicalModel) -> str:
    artifact_id = str(uuid4())
    _PHYSICAL_ARTIFACTS[artifact_id] = physical_model
    return artifact_id


def get_physical_artifact(artifact_id: str) -> PhysicalModel | None:
    return _PHYSICAL_ARTIFACTS.get(artifact_id)
