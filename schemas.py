from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, Field


class EntityDefinition(BaseModel):
    name: str
    description: str
    attributes: List[str] = Field(default_factory=list)


class RelationshipDefinition(BaseModel):
    from_entity: str
    to_entity: str
    cardinality: str
    description: str
    label: Optional[str] = None


class ConceptualModel(BaseModel):
    title: str = ""
    scope: str = ""
    requirement: str = ""
    rag_context_used: str = ""
    entities: List[EntityDefinition]
    relationships: List[RelationshipDefinition]
    business_rules: List[str] = Field(default_factory=list)
    conceptual_summary: str = ""
    diagram_description: str = ""
    er_diagram_mermaid: str = ""


#editd by mani
class ConceptualUpdatePatch(BaseModel):
    entities_to_add: List[EntityDefinition] = Field(default_factory=list)
    relationships_to_add_or_update: List[RelationshipDefinition] = Field(default_factory=list)


class LogicalColumn(BaseModel):
    name: str
    type: str
    nullable: bool


class ForeignKeyDefinition(BaseModel):
    column: str
    references_table: str
    references_column: str


class LogicalTable(BaseModel):
    table_name: str
    source_entity: str
    columns: List[LogicalColumn]
    primary_key: List[str]
    foreign_keys: List[ForeignKeyDefinition] = Field(default_factory=list)


class LogicalModel(BaseModel):
    source_entities: List[str]
    tables: List[LogicalTable]
    relationships: List[RelationshipDefinition]
    normalization_notes: List[str] = Field(default_factory=list)
    er_diagram_mermaid: str = ""


class PhysicalModelTemplate(BaseModel):
    status: str
    message: str
    prompt_preview: str
    next_step_template: Dict[str, Any]
    logical_tables_received: int


#added by swamy
class PhysicalColumn(BaseModel):
    name: str
    column_data_type: str
    nullable: bool


#added by swamy
class PhysicalIndex(BaseModel):
    index_name: str
    table_name: str
    columns: List[str]
    unique: bool = False


#added by swamy
class PhysicalTable(BaseModel):
    table_name: str
    columns: List[PhysicalColumn]
    primary_key: List[str]
    foreign_keys: List[ForeignKeyDefinition] = Field(default_factory=list)
    indexes: List[PhysicalIndex] = Field(default_factory=list)


#added by swamy
class PhysicalModel(BaseModel):
    tables: List[PhysicalTable]
    indexes: List[PhysicalIndex] = Field(default_factory=list)
    ddl: List[str] = Field(default_factory=list)
    er_diagram_mermaid: str = ""


class AnalyticsVectorResponsePayload(BaseModel):
    asset_category: str
    asset_name: str
    asset_attribute: str


class AnalyticsVectorDocument(BaseModel):
    doc_id: str
    asset_category: str
    asset_name: str
    asset_attribute: str
    entity_name: str = Field(default="", validation_alias=AliasChoices("entity_name", "value_stream"))
    attribute_name: str
    attribute_description: str = ""
    entity_description: str = Field(default="", validation_alias=AliasChoices("entity_description", "value_stream_description"))
    source_description: str = ""
    source_system: str = ""
    asset_type: str = ""
    type_classification: str = ""
    business_classification: str = ""
    category: str = ""
    data_classification: str = ""
    physical_region: str = ""
    is_pii_column: bool | None = None
    is_sensitive_column: bool | None = None
    lineage_assets: List[str] | None = None
    join_keys: List[str] | None = None
    vector_text: str = ""
    response_payload: AnalyticsVectorResponsePayload


class AnalyticsRequest(BaseModel):
    attribute_name: str = Field(..., description="Business attribute requested by the user.")
    attribute_description: str = Field(
        default="",
        description="Optional business description or criteria supplied by the user.",
    )
    region: str = Field(
        default="",
        description="Optional region filter. When supplied, analytics search is limited to glossary rows from that region.",
    )
    selected_value_stream: str = Field(
        default="",
        validation_alias=AliasChoices("selected_value_stream", "selected_asset_name"),
        description="Optional GDA value stream selected by a human when multiple governed value streams are returned.",
    )
    brief_problem_statement: str = Field(
        default="",
        description="Optional business use-case context from the requirement workbook.",
    )
    system_requirements: str = Field(
        default="",
        description="Optional system requirements context from the requirement workbook.",
    )


class AnalyticsBatchRequest(BaseModel):
    queries: List[AnalyticsRequest] = Field(
        ...,
        description="One or more analytics attribute requests, usually read from uploaded Excel rows.",
    )


class AnalyticsOutputMatch(BaseModel):
    doc_id: str = Field(default="", exclude=True)
    asset_category: str = Field(
        validation_alias=AliasChoices("asset_category", "layer"),
        serialization_alias="layer",
    )
    asset_name: str = Field(
        validation_alias=AliasChoices("asset_name", "value_stream_name"),
        serialization_alias="value_stream_name",
    )
    asset_attribute: str = Field(
        validation_alias=AliasChoices("asset_attribute", "value_stream_attribute"),
        serialization_alias="value_stream_attribute",
    )
    entity_name: str = Field(
        default="",
        validation_alias=AliasChoices("entity_name", "value_stream"),
        serialization_alias="value_stream",
    )
    entity_description: str = Field(
        default="",
        validation_alias=AliasChoices("entity_description", "value_stream_description"),
        serialization_alias="value_stream_description",
    )
    attribute_name: str = ""
    attribute_description: str = ""
    source_description: str = ""
    lineage_assets: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("lineage_assets", "lineage_value_streams"),
        serialization_alias="lineage_value_streams",
    )
    lineage_details: List[Dict[str, str]] = Field(default_factory=list)
    join_keys: List[str] = Field(default_factory=list)
    relevance_score: float = Field(default=0.0, exclude=True)
    recommendation_score: float = 0.0
    region: str = ""
    match_phase: str = ""
    phase_weight: float = 0.0
    fuzzy_score: float = Field(default=0.0, exclude=True)
    semantic_score: float = Field(default=0.0, exclude=True)
    justification: str = ""


class AnalyticsLayerSummary(BaseModel):
    layer: str
    relevant_match_count: int = 0


class AnalyticsRetrievalMetadata(BaseModel):
    retrieval_strategy: str = "phase1_exact_phase2_rapidfuzz_phase3_faiss"
    documents_considered: int = 0
    region_filtered_documents: int = 0
    returned_matches: int = 0
    phase_used: str = ""
    semantic_index_enabled: bool = False
    available_regions: List[str] = Field(default_factory=list)


class AnalyticsResponse(BaseModel):
    original_query: str
    requested_attribute_name: str = ""
    requested_attribute_description: str = ""
    requested_region: str = ""
    status: str = ""
    answer: str
    match_phase: str = ""
    human_in_loop_required: bool = False
    human_in_loop_prompt: str = ""
    human_selection_options: List[str] = Field(default_factory=list)
    selected_details: Dict[str, Any] = Field(default_factory=dict)
    relevant_matches: List[AnalyticsOutputMatch] = Field(default_factory=list)
    layer_summary: List[AnalyticsLayerSummary] = Field(default_factory=list)
    retrieval_metadata: AnalyticsRetrievalMetadata = Field(default_factory=AnalyticsRetrievalMetadata)


class AnalyticsBatchResult(BaseModel):
    query: str
    output: AnalyticsResponse


class AnalyticsBatchResponse(BaseModel):
    total_queries: int
    output_json_path: str
    results: List[AnalyticsBatchResult]


class AnalyticsBatchSummaryItem(BaseModel):
    query: str = ""
    status: str = ""
    match_phase: str = ""
    relevant_match_count: int = 0
    human_in_loop_required: bool = False
    answer: str = ""


class AnalyticsBatchSummaryResponse(BaseModel):
    total_queries: int
    summaries: List[AnalyticsBatchSummaryItem] = Field(default_factory=list)


class AnalyticsRequirementRow(BaseModel):
    row_number: int
    business_attribute: str
    business_definition: str
    region: str = ""
    value_stream: str = ""
    brief_problem_statement: str = ""
    system_requirements: str = ""
    attribute_name: str
    attribute_description: str
    selected_value_stream: str = ""
    query: str = ""


class AnalyticsRequirementResult(BaseModel):
    requirement: AnalyticsRequirementRow
    output: AnalyticsResponse


class AnalyticsRequirementProcessResponse(BaseModel):
    source_file_name: str
    total_rows: int
    matched_rows: int = 0
    no_match_rows: int = 0
    requires_human_selection_rows: int = 0
    results: List[AnalyticsRequirementResult] = Field(default_factory=list)


class AnalyticsLLMRelevanceDecision(BaseModel):
    doc_id: str
    keep: bool = False
    semantic_score: float | None = None
    reason: str = ""


class AnalyticsLLMRelevanceSelection(BaseModel):
    answer: str = ""
    decisions: List[AnalyticsLLMRelevanceDecision] = Field(default_factory=list)


class ConceptualRequest(BaseModel):
    requirement: str = Field(..., description="Business requirement or use case from the user.")


class LogicalRequest(BaseModel):
    conceptual_output: ConceptualModel


class ModelingRequest(BaseModel):
    requirement: str = Field(..., description="Business requirement or use case from the user.")
    artifact_id: Optional[str] = Field(
        default=None,
        description="Existing conceptual artifact to update or approve using the same /orchestrate endpoint.",
    )
    from_entity: Optional[str] = None
    to_entity: Optional[str] = None
    cardinality: str = "M:N"
    description: Optional[str] = None
    label: Optional[str] = None


class ConceptualResponse(BaseModel):
    rag_context: str
    conceptual_model: ConceptualModel
    mermaid_diagram: str
    artifact_id: str
    view_url: str
    download_mermaid_url: str
    download_json_url: str


class OrchestratorResponse(BaseModel):
    requirement: str
    conceptual_output: Optional[ConceptualModel] = None
    logical_output: Optional[LogicalModel] = None
    physical_output: Optional[PhysicalModel] = None  #added by swamy
    conceptual_status: Optional[str] = None
    agent_final_answer: str = ""
    conceptual_artifact_id: Optional[str] = None
    conceptual_view_url: Optional[str] = None
    conceptual_download_mermaid_url: Optional[str] = None
    conceptual_download_json_url: Optional[str] = None
    logical_artifact_id: Optional[str] = None
    logical_view_url: Optional[str] = None
    logical_download_mermaid_url: Optional[str] = None
    logical_download_json_url: Optional[str] = None
    physical_artifact_id: Optional[str] = None
    physical_view_url: Optional[str] = None
    physical_download_mermaid_url: Optional[str] = None
    physical_download_json_url: Optional[str] = None




