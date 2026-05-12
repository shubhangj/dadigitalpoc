from __future__ import annotations
import json
import logging
import re
from pathlib import Path

logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
)

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

try:
    from analytics_workbook import parse_requirement_workbook
    from analytics_service import (
        record_analytics_query_result,
        search_analytics,
        search_analytics_batch,
        warm_analytics_index,
    )
    from artifact_store import (
        get_conceptual_artifact,
        get_logical_artifact,
        get_physical_artifact,
        set_conceptual_artifact_status,
        save_conceptual_artifact,
        save_logical_artifact,
        save_physical_artifact,
        update_conceptual_artifact,
    )
    from project_history_store import (
        read_project,
        read_project_store,
        write_project,
        write_project_store,
    )
    from config import warm_models_on_startup_enabled
    from schemas import (
        AnalyticsRequest,
        AnalyticsBatchRequest,
        AnalyticsBatchResponse,
        AnalyticsBatchSummaryItem,
        AnalyticsBatchSummaryResponse,
        AnalyticsRequirementProcessResponse,
        AnalyticsRequirementResult,
        AnalyticsRequirementRow,
        AnalyticsResponse,
        ConceptualModel,
        EntityDefinition,
        LogicalModel,
        ModelingRequest,
        OrchestratorResponse,
        PhysicalModel,
        RelationshipDefinition,
    )
    from utils.mermaid_builder import build_logical_mermaid, build_mermaid, build_physical_mermaid
except ImportError:  # pragma: no cover - supports package-style imports
    from .analytics_workbook import parse_requirement_workbook
    from .analytics_service import (
        record_analytics_query_result,
        search_analytics,
        search_analytics_batch,
        warm_analytics_index,
    )
    from .artifact_store import (
        get_conceptual_artifact,
        get_logical_artifact,
        get_physical_artifact,
        set_conceptual_artifact_status,
        save_conceptual_artifact,
        save_logical_artifact,
        save_physical_artifact,
        update_conceptual_artifact,
    )
    from .project_history_store import (
        read_project,
        read_project_store,
        write_project,
        write_project_store,
    )
    from .config import warm_models_on_startup_enabled
    from .schemas import (
        AnalyticsRequest,
        AnalyticsBatchRequest,
        AnalyticsBatchResponse,
        AnalyticsBatchSummaryItem,
        AnalyticsBatchSummaryResponse,
        AnalyticsRequirementProcessResponse,
        AnalyticsRequirementResult,
        AnalyticsRequirementRow,
        AnalyticsResponse,
        ConceptualModel,
        EntityDefinition,
        LogicalModel,
        ModelingRequest,
        OrchestratorResponse,
        PhysicalModel,
        RelationshipDefinition,
    )
    from .utils.mermaid_builder import build_logical_mermaid, build_mermaid, build_physical_mermaid

try:
    from rag import warm_rag
except ImportError:  # pragma: no cover - supports package-style imports
    try:
        from .rag import warm_rag
    except ImportError:  # pragma: no cover
        def warm_rag() -> None:
            return None

_modeling_runtime_error: Exception | None = None
try:
    from .tools import (
        conceptual_model_core,
        conceptual_update_patch_core,
        ensure_connected_conceptual_model,
        logical_model_core,
        physical_model_core,
    )
except ImportError:
    try:
        from tools import (
            conceptual_model_core,
            conceptual_update_patch_core,
            ensure_connected_conceptual_model,
            logical_model_core,
            physical_model_core,
        )
    except ImportError as exc:  # pragma: no cover
        conceptual_model_core = None
        conceptual_update_patch_core = None
        ensure_connected_conceptual_model = None
        logical_model_core = None
        physical_model_core = None
        _modeling_runtime_error = exc

app = FastAPI(
    title="Agentic Data Modeling Workflow",
    version="2.0.0",
    description=(
        "Single-entry agentic API. The user sends a requirement to /orchestrate, "
        "the orchestrator invokes the agent, and the agent decides which tools to use."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DIGITAL_DA_HTML_PATH = Path(__file__).with_name("AI Data Discovery.html")


@app.on_event("startup")
def _warm_models_on_startup() -> None:
    if not warm_models_on_startup_enabled():
        logging.info("Startup warmup disabled.")
        return
    warm_rag()
    try:
        warm_analytics_index()
    except Exception as exc:
        logging.warning("Analytics warmup skipped: %s", exc)


def _apply_generated_mermaid(conceptual: ConceptualModel) -> ConceptualModel:
    generated_mermaid = build_mermaid(conceptual)
    return conceptual.model_copy(update={"er_diagram_mermaid": generated_mermaid})


def _apply_generated_logical_mermaid(logical: LogicalModel) -> LogicalModel:
    generated_mermaid = build_logical_mermaid(logical)
    return logical.model_copy(update={"er_diagram_mermaid": generated_mermaid})


def _apply_generated_physical_mermaid(physical: PhysicalModel) -> PhysicalModel:
    generated_mermaid = build_physical_mermaid(physical)
    return physical.model_copy(update={"er_diagram_mermaid": generated_mermaid})


def _build_artifact_links(request: Request, stage: str, artifact_id: str) -> dict[str, str]:
    base_url = str(request.base_url).rstrip("/")
    return {
        "view_url": f"{base_url}/{stage}/view/{artifact_id}",
        "download_mermaid_url": f"{base_url}/{stage}/download/mermaid/{artifact_id}",
        "download_json_url": f"{base_url}/{stage}/download/json/{artifact_id}",
    }


def _require_modeling_runtime() -> None:
    if _modeling_runtime_error is not None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Modeling dependencies are not available on this system. "
                f"Import error: {_modeling_runtime_error}"
            ),
        )


#editd by mani
def _generation_failed(step_name: str, exc: Exception) -> None:
    logging.exception("%s generation failed. No fallback artifact will be created.", step_name)
    raise HTTPException(
        status_code=502,
        detail=f"{step_name} generation or validation failed. Please verify GEMINI_API_KEY, GEMINI_MODEL, and model output format.",
    ) from exc


#editd by mani
def _normalized_entity_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


#editd by mani
def _resolve_conceptual_entity_name(conceptual: ConceptualModel, entity_name: str) -> str | None:
    target = _normalized_entity_name(entity_name)
    for entity in conceptual.entities:
        if _normalized_entity_name(entity.name) == target:
            return entity.name
    return None


#editd by mani
def _resolve_instruction_entities(conceptual: ConceptualModel, instruction: str) -> list[str]:
    instruction_text = instruction.lower().replace("_", " ")
    matches = []
    for entity in conceptual.entities:
        aliases = {
            entity.name.lower(),
            entity.name.lower().replace("_", " "),
            entity.name.lower().replace(" ", "_"),
        }
        positions = [
            instruction_text.find(alias.replace("_", " "))
            for alias in aliases
            if instruction_text.find(alias.replace("_", " ")) >= 0
        ]
        if positions:
            matches.append((min(positions), entity.name))
    matches.sort(key=lambda item: item[0])

    ordered_entities = []
    for _, entity_name in matches:
        if entity_name not in ordered_entities:
            ordered_entities.append(entity_name)
    return ordered_entities


#editd by mani
def _upsert_conceptual_relationship(
    conceptual: ConceptualModel,
    from_entity: str,
    to_entity: str,
    cardinality: str,
    description: str | None,
    label: str | None,
) -> ConceptualModel:
    relationships = [relationship.model_copy() for relationship in conceptual.relationships]
    existing_index = None

    for index, relationship in enumerate(relationships):
        if {
            _normalized_entity_name(relationship.from_entity),
            _normalized_entity_name(relationship.to_entity),
        } == {
            _normalized_entity_name(from_entity),
            _normalized_entity_name(to_entity),
        }:
            existing_index = index
            break

    relationship_payload = RelationshipDefinition(
        from_entity=from_entity,
        to_entity=to_entity,
        cardinality=cardinality,
        description=description or f"{from_entity} is directly related to {to_entity} at the conceptual business level.",
        label=label or "relates to",
    )

    if existing_index is None:
        relationships.append(relationship_payload)
    else:
        relationships[existing_index] = relationship_payload

    return conceptual.model_copy(update={"relationships": relationships})


#editd by mani
def _upsert_conceptual_entity(
    conceptual: ConceptualModel,
    entity_name: str,
    description: str | None,
    attributes: list[str] | None,
) -> ConceptualModel:
    entities = [entity.model_copy() for entity in conceptual.entities]
    normalized_entity_name = _normalized_entity_name(entity_name)

    for entity in entities:
        if _normalized_entity_name(entity.name) == normalized_entity_name:
            return conceptual

    entities.append(
        EntityDefinition(
            name=entity_name,
            description=description or f"Business entity added from conceptual update instruction for {entity_name}.",
            attributes=attributes or [],
        )
    )
    return conceptual.model_copy(update={"entities": entities})


#editd by mani
def _is_approval_instruction(requirement: str) -> bool:
    requirement_text = requirement.strip().lower()
    return bool(re.fullmatch(r"(approve|approved|save|saved|proceed|continue)", requirement_text))


#editd by mani
def _parse_cardinality_from_text(requirement: str, fallback: str) -> str:
    requirement_text = requirement.lower()
    if "1:n" in requirement_text or "one-to-many" in requirement_text or "one to many" in requirement_text:
        return "1:N"
    if "n:1" in requirement_text or "many-to-one" in requirement_text or "many to one" in requirement_text:
        return "N:1"
    if "1:1" in requirement_text or "one-to-one" in requirement_text or "one to one" in requirement_text:
        return "1:1"
    if "m:n" in requirement_text or "many-to-many" in requirement_text or "many to many" in requirement_text:
        return "M:N"
    return fallback


def _build_mermaid_html(title: str, payload: dict[str, object], json_filename: str, mermaid_text: str) -> str:
    payload_json = json.dumps(payload, indent=2)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Conceptual ER Diagram</title>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
  </script>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f7fb; color: #1f2937; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; background: white; border-radius: 12px; padding: 24px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08); }}
    .toolbar {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }}
    button {{ border: 0; border-radius: 8px; padding: 10px 14px; background: #0f766e; color: white; cursor: pointer; font-size: 14px; }}
    pre {{ background: #111827; color: #e5e7eb; padding: 16px; border-radius: 10px; overflow-x: auto; white-space: pre-wrap; }}
    .section {{ margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{title}</h1>
    <div class="toolbar">
      <button onclick="downloadMermaid()">Download .mmd</button>
      <button onclick="downloadJson()">Download JSON</button>
    </div>
    <div class="mermaid">
{mermaid_text}
    </div>
    <div class="section"><h2>Mermaid Source</h2><pre id="source"></pre></div>
    <div class="section"><h2>Model JSON</h2><pre id="model-json"></pre></div>
  </div>
  <script>
    const mermaidText = {mermaid_text!r};
    const modelJson = {payload_json!r};
    document.getElementById("source").textContent = mermaidText;
    document.getElementById("model-json").textContent = modelJson;
    function downloadMermaid() {{
      const blob = new Blob([mermaidText], {{ type: "text/plain;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "er_diagram.mmd";
      link.click();
      URL.revokeObjectURL(url);
    }}
    function downloadJson() {{
      const blob = new Blob([modelJson], {{ type: "application/json;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = {json_filename!r};
      link.click();
      URL.revokeObjectURL(url);
    }}
  </script>
</body>
</html>"""


#editd by mani
def _build_orchestrator_response(
    request: Request,
    requirement: str,
    conceptual: ConceptualModel | None,
    logical: LogicalModel | None,
    physical: PhysicalModel | None,
    conceptual_artifact_id: str | None,
    logical_artifact_id: str | None,
    physical_artifact_id: str | None,
    conceptual_status: str | None,
    agent_final_answer: str,
) -> OrchestratorResponse:
    conceptual_links = {
        "view_url": None,
        "download_mermaid_url": None,
        "download_json_url": None,
    }
    logical_links = {
        "view_url": None,
        "download_mermaid_url": None,
        "download_json_url": None,
    }
    physical_links = {
        "view_url": None,
        "download_mermaid_url": None,
        "download_json_url": None,
    }

    if conceptual_artifact_id:
        conceptual_links = _build_artifact_links(request, "conceptual", conceptual_artifact_id)
    if logical_artifact_id:
        logical_links = _build_artifact_links(request, "logical", logical_artifact_id)
    if physical_artifact_id:
        physical_links = _build_artifact_links(request, "physical", physical_artifact_id)

    return OrchestratorResponse(
        requirement=requirement,
        conceptual_output=conceptual,
        logical_output=logical,
        physical_output=physical,
        conceptual_status=conceptual_status,
        agent_final_answer=agent_final_answer,
        conceptual_artifact_id=conceptual_artifact_id,
        conceptual_view_url=conceptual_links["view_url"],
        conceptual_download_mermaid_url=conceptual_links["download_mermaid_url"],
        conceptual_download_json_url=conceptual_links["download_json_url"],
        logical_artifact_id=logical_artifact_id,
        logical_view_url=logical_links["view_url"],
        logical_download_mermaid_url=logical_links["download_mermaid_url"],
        logical_download_json_url=logical_links["download_json_url"],
        physical_artifact_id=physical_artifact_id,
        physical_view_url=physical_links["view_url"],
        physical_download_mermaid_url=physical_links["download_mermaid_url"],
        physical_download_json_url=physical_links["download_json_url"],
    )


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def digital_da_home() -> FileResponse:
    return FileResponse(DIGITAL_DA_HTML_PATH, media_type="text/html")


@app.get("/digital-da", response_class=HTMLResponse)
def digital_da_page() -> FileResponse:
    return FileResponse(DIGITAL_DA_HTML_PATH, media_type="text/html")


@app.post(
    "/analytics",
    response_model=AnalyticsResponse,
    response_model_by_alias=True,
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
)
def analytics_endpoint(payload: AnalyticsRequest) -> AnalyticsResponse:
    try:
        response = search_analytics(
            attribute_name=payload.attribute_name,
            attribute_description=payload.attribute_description,
            region=payload.region,
            selected_asset_name=payload.selected_value_stream,
            brief_problem_statement=payload.brief_problem_statement,
            system_requirements=payload.system_requirements,
        )
        record_analytics_query_result(response)
        return response
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.exception("Analytics search failed")
        raise HTTPException(
            status_code=502,
            detail="Analytics retrieval failed. Verify glossary JSON path and semantic search dependencies.",
        ) from exc


@app.post(
    "/analytics/batch",
    response_model=AnalyticsBatchResponse,
    response_model_by_alias=True,
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
)
def analytics_batch_endpoint(payload: AnalyticsBatchRequest) -> AnalyticsBatchResponse:
    try:
        return AnalyticsBatchResponse.model_validate(search_analytics_batch(payload.queries))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.exception("Analytics batch search failed")
        raise HTTPException(
            status_code=502,
            detail="Analytics batch retrieval failed. Verify glossary JSON path and semantic search dependencies.",
        ) from exc


@app.post(
    "/analytics/batch/summary",
    response_model=AnalyticsBatchSummaryResponse,
    response_model_by_alias=True,
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
)
def analytics_batch_summary_endpoint(payload: AnalyticsBatchRequest) -> AnalyticsBatchSummaryResponse:
    try:
        batch_payload = search_analytics_batch(payload.queries)
        summaries: list[AnalyticsBatchSummaryItem] = []

        for batch_result in batch_payload.get("results", []):
            output = AnalyticsResponse.model_validate(batch_result.get("output", {}))
            summaries.append(
                AnalyticsBatchSummaryItem(
                    query=batch_result.get("query", ""),
                    status=output.status,
                    match_phase=output.match_phase,
                    relevant_match_count=len(output.relevant_matches),
                    human_in_loop_required=output.human_in_loop_required,
                    answer=output.answer,
                )
            )

        return AnalyticsBatchSummaryResponse(
            total_queries=len(payload.queries),
            summaries=summaries,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.exception("Analytics batch summary failed")
        raise HTTPException(
            status_code=502,
            detail="Analytics batch summary failed. Verify glossary JSON path and semantic search dependencies.",
        ) from exc


@app.post(
    "/analytics/requirements/process",
    response_model=AnalyticsRequirementProcessResponse,
    response_model_by_alias=True,
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
)
async def analytics_requirement_process_endpoint(
    file: UploadFile = File(...),
) -> AnalyticsRequirementProcessResponse:
    try:
        if not file.filename:
            raise ValueError("A requirement workbook file is required.")

        file_bytes = await file.read()
        requirements = parse_requirement_workbook(file_bytes, file.filename)
        batch_payload = search_analytics_batch(requirements)

        results: list[AnalyticsRequirementResult] = []
        matched_rows = 0
        no_match_rows = 0
        requires_human_selection_rows = 0

        for requirement, batch_result in zip(requirements, batch_payload.get("results", [])):
            output = AnalyticsResponse.model_validate(batch_result.get("output", {}))
            if output.status == "matched":
                matched_rows += 1
            elif output.status == "requires_human_selection":
                requires_human_selection_rows += 1
            else:
                no_match_rows += 1

            results.append(
                AnalyticsRequirementResult(
                    requirement=AnalyticsRequirementRow.model_validate(requirement),
                    output=output,
                )
            )

        return AnalyticsRequirementProcessResponse(
            source_file_name=file.filename,
            total_rows=len(requirements),
            matched_rows=matched_rows,
            no_match_rows=no_match_rows,
            requires_human_selection_rows=requires_human_selection_rows,
            results=results,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.exception("Analytics requirement workbook processing failed")
        raise HTTPException(
            status_code=502,
            detail="Requirement workbook processing failed. Verify the workbook schema and analytics glossary setup.",
        ) from exc


@app.get("/projects/store")
def get_projects_store() -> dict:
    return read_project_store()


@app.put("/projects/store")
def put_projects_store(store: dict) -> dict:
    return write_project_store(store)


@app.get("/projects/{project_id}")
def get_project(project_id: str) -> dict:
    project = read_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@app.put("/projects/{project_id}")
def put_project(project_id: str, project: dict) -> dict:
    project = dict(project)
    project["project_id"] = project_id
    return write_project(project)


@app.post("/orchestrate", response_model=OrchestratorResponse)
def orchestrate_endpoint(payload: ModelingRequest, request: Request) -> OrchestratorResponse:
    logging.info("/orchestrate endpoint called")
    _require_modeling_runtime()
    requirement = payload.requirement
    artifact_id = payload.artifact_id

    if artifact_id:
        conceptual = get_conceptual_artifact(artifact_id)
        if conceptual is None:
            raise HTTPException(status_code=404, detail="Conceptual artifact not found.")

        if _is_approval_instruction(requirement):
            conceptual = _apply_generated_mermaid(conceptual)

            try:
                logical_payload = logical_model_core(conceptual.model_dump())
            except Exception as exc:
                _generation_failed("Logical model", exc)

            logical = _apply_generated_logical_mermaid(LogicalModel.model_validate(logical_payload))

            try:
                physical_payload = physical_model_core(logical.model_dump())
            except Exception as exc:
                _generation_failed("Physical model", exc)

            physical = _apply_generated_physical_mermaid(PhysicalModel.model_validate(physical_payload))

            update_conceptual_artifact(artifact_id, conceptual)
            set_conceptual_artifact_status(artifact_id, "approved")
            logical_artifact_id = save_logical_artifact(logical)
            physical_artifact_id = save_physical_artifact(physical)

            return _build_orchestrator_response(
                request=request,
                requirement=conceptual.requirement,
                conceptual=conceptual,
                logical=logical,
                physical=physical,
                conceptual_artifact_id=artifact_id,
                logical_artifact_id=logical_artifact_id,
                physical_artifact_id=physical_artifact_id,
                conceptual_status="approved",
                agent_final_answer="Conceptual draft approved and used to generate logical and physical models.",
            )

        from_entity = payload.from_entity
        to_entity = payload.to_entity

        if from_entity:
            from_entity = _resolve_conceptual_entity_name(conceptual, from_entity)
        if to_entity:
            to_entity = _resolve_conceptual_entity_name(conceptual, to_entity)

        if not from_entity or not to_entity:
            try:
                patch = conceptual_update_patch_core(conceptual.model_dump(), requirement)
            except Exception as exc:
                _generation_failed("Conceptual update", exc)

            for entity in patch.get("entities_to_add", []):
                updated_name = entity.get("name", "")
                if not updated_name:
                    continue
                conceptual = _upsert_conceptual_entity(
                    conceptual=conceptual,
                    entity_name=updated_name,
                    description=entity.get("description"),
                    attributes=entity.get("attributes", []),
                )

            relationships = patch.get("relationships_to_add_or_update", [])
            if not relationships:
                resolved_entities = _resolve_instruction_entities(conceptual, requirement)
                if len(resolved_entities) >= 2:
                    relationships = [
                        {
                            "from_entity": resolved_entities[0],
                            "to_entity": resolved_entities[1],
                            "cardinality": _parse_cardinality_from_text(requirement, payload.cardinality),
                            "description": payload.description,
                            "label": payload.label,
                        }
                    ]

            if not relationships:
                raise HTTPException(
                    status_code=400,
                    detail="Could not understand the conceptual update request. Mention the entities to connect or the new entity to add.",
                )

            updated_conceptual = conceptual
            for relationship in relationships:
                resolved_from_entity = _resolve_conceptual_entity_name(
                    updated_conceptual,
                    relationship.get("from_entity", ""),
                ) or relationship.get("from_entity", "")
                resolved_to_entity = _resolve_conceptual_entity_name(
                    updated_conceptual,
                    relationship.get("to_entity", ""),
                ) or relationship.get("to_entity", "")

                if not resolved_from_entity or not resolved_to_entity:
                    continue

                updated_conceptual = _upsert_conceptual_relationship(
                    conceptual=updated_conceptual,
                    from_entity=resolved_from_entity,
                    to_entity=resolved_to_entity,
                    cardinality=_parse_cardinality_from_text(
                        requirement,
                        relationship.get("cardinality", payload.cardinality),
                    ),
                    description=relationship.get("description") or payload.description,
                    label=relationship.get("label") or payload.label,
                )
        else:
            updated_conceptual = _upsert_conceptual_relationship(
                conceptual=conceptual,
                from_entity=from_entity,
                to_entity=to_entity,
                cardinality=_parse_cardinality_from_text(requirement, payload.cardinality),
                description=payload.description,
                label=payload.label,
            )

        updated_conceptual = ConceptualModel.model_validate(
            ensure_connected_conceptual_model(updated_conceptual.model_dump())
        )
        updated_conceptual = _apply_generated_mermaid(updated_conceptual)
        update_conceptual_artifact(artifact_id, updated_conceptual)
        set_conceptual_artifact_status(artifact_id, "draft")

        return _build_orchestrator_response(
            request=request,
            requirement=updated_conceptual.requirement,
            conceptual=updated_conceptual,
            logical=None,
            physical=None,
            conceptual_artifact_id=artifact_id,
            logical_artifact_id=None,
            physical_artifact_id=None,
            conceptual_status="draft",
            agent_final_answer=f"Conceptual relationship updated between {from_entity} and {to_entity}. Review the revised draft and send requirement as 'approve' or 'save' with the same artifact_id when ready.",
        )

    try:
        conceptual_payload = conceptual_model_core(requirement)
    except Exception as exc:
        _generation_failed("Conceptual model", exc)

    conceptual = _apply_generated_mermaid(ConceptualModel.model_validate(conceptual_payload))
    conceptual_artifact_id = save_conceptual_artifact(conceptual, status="draft")
    return _build_orchestrator_response(
        request=request,
        requirement=requirement,
        conceptual=conceptual,
        logical=None,
        physical=None,
        conceptual_artifact_id=conceptual_artifact_id,
        logical_artifact_id=None,
        physical_artifact_id=None,
        conceptual_status="draft",
        agent_final_answer="Conceptual draft generated. Review the conceptual ER and use the same /orchestrate endpoint with artifact_id to update relationships or send 'approve' to continue.",
    )


@app.get("/conceptual/view/{artifact_id}", response_class=HTMLResponse)
def conceptual_view(artifact_id: str) -> HTMLResponse:
    conceptual = get_conceptual_artifact(artifact_id)
    if conceptual is None:
        raise HTTPException(status_code=404, detail="Conceptual artifact not found.")
    return HTMLResponse(
        content=_build_mermaid_html(
            "Conceptual ER Diagram",
            conceptual.model_dump(),
            "conceptual_model.json",
            conceptual.er_diagram_mermaid,
        )
    )


@app.get("/conceptual/download/mermaid/{artifact_id}")
def download_mermaid_artifact(artifact_id: str) -> PlainTextResponse:
    conceptual = get_conceptual_artifact(artifact_id)
    if conceptual is None:
        raise HTTPException(status_code=404, detail="Conceptual artifact not found.")
    return PlainTextResponse(
        content=conceptual.er_diagram_mermaid,
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="er_diagram.mmd"'},
    )


@app.get("/conceptual/download/json/{artifact_id}")
def download_conceptual_json_artifact(artifact_id: str) -> PlainTextResponse:
    conceptual = get_conceptual_artifact(artifact_id)
    if conceptual is None:
        raise HTTPException(status_code=404, detail="Conceptual artifact not found.")
    return PlainTextResponse(
        content=json.dumps(conceptual.model_dump(), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="conceptual_model.json"'},
    )


@app.get("/logical/view/{artifact_id}", response_class=HTMLResponse)
def logical_view(artifact_id: str) -> HTMLResponse:
    logical = get_logical_artifact(artifact_id)
    if logical is None:
        raise HTTPException(status_code=404, detail="Logical artifact not found.")
    return HTMLResponse(
        content=_build_mermaid_html(
            "Logical ER Diagram",
            logical.model_dump(),
            "logical_model.json",
            logical.er_diagram_mermaid,
        )
    )


@app.get("/logical/download/mermaid/{artifact_id}")
def download_logical_mermaid_artifact(artifact_id: str) -> PlainTextResponse:
    logical = get_logical_artifact(artifact_id)
    if logical is None:
        raise HTTPException(status_code=404, detail="Logical artifact not found.")
    return PlainTextResponse(
        content=logical.er_diagram_mermaid,
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="logical_er_diagram.mmd"'},
    )


@app.get("/logical/download/json/{artifact_id}")
def download_logical_json_artifact(artifact_id: str) -> PlainTextResponse:
    logical = get_logical_artifact(artifact_id)
    if logical is None:
        raise HTTPException(status_code=404, detail="Logical artifact not found.")
    return PlainTextResponse(
        content=json.dumps(logical.model_dump(), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="logical_model.json"'},
    )


@app.get("/physical/view/{artifact_id}", response_class=HTMLResponse)
def physical_view(artifact_id: str) -> HTMLResponse:
    physical = get_physical_artifact(artifact_id)
    if physical is None:
        raise HTTPException(status_code=404, detail="Physical artifact not found.")
    return HTMLResponse(
        content=_build_mermaid_html(
            "Physical ER Diagram",
            physical.model_dump(),
            "physical_model.json",
            physical.er_diagram_mermaid,
        )
    )


@app.get("/physical/download/mermaid/{artifact_id}")
def download_physical_mermaid_artifact(artifact_id: str) -> PlainTextResponse:
    physical = get_physical_artifact(artifact_id)
    if physical is None:
        raise HTTPException(status_code=404, detail="Physical artifact not found.")
    return PlainTextResponse(
        content=physical.er_diagram_mermaid,
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="physical_er_diagram.mmd"'},
    )


@app.get("/physical/download/json/{artifact_id}")
def download_physical_json_artifact(artifact_id: str) -> PlainTextResponse:
    physical = get_physical_artifact(artifact_id)
    if physical is None:
        raise HTTPException(status_code=404, detail="Physical artifact not found.")
    return PlainTextResponse(
        content=json.dumps(physical.model_dump(), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="physical_model.json"'},
    )
