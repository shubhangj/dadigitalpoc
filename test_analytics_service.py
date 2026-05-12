from analytics_service import (
    AnalyticsIndex,
    GlossaryRecord,
    _build_response,
    _build_search_request,
    _expand_attribute_name,
    _filter_matches_for_selected_asset,
    _normalize_name,
    _resolve_selected_asset_name,
    _run_matching_pipeline,
)
from schemas import AnalyticsRetrievalMetadata


def make_record(
    asset_category: str,
    asset_name: str,
    entity_name: str,
    attribute_name: str,
    attribute_description: str,
) -> GlossaryRecord:
    return GlossaryRecord(
        doc_id=f"{asset_category}:{asset_name}:{attribute_name}",
        asset_category=asset_category,
        asset_name=asset_name,
        asset_attribute=f"{entity_name}.{attribute_name}",
        entity_name=entity_name,
        attribute_name=attribute_name,
        attribute_description=attribute_description,
        entity_description=f"{entity_name} customer facility entity",
        source_description=f"{entity_name} lineage source",
        lineage_assets=[],
        join_keys=[],
        region="UK",
        normalized_attribute=_normalize_name(attribute_name),
        expanded_attribute=_expand_attribute_name(attribute_name),
        semantic_text=f"{attribute_name} {attribute_description} {entity_name}",
    )


def test_direct_mda_matches_are_returned_with_available_gda_matches():
    request = _build_search_request(
        "customer_id",
        "Unique identifier of customer id",
        "UK",
    )
    records = [
        make_record(
            "MDA",
            "MDA.CUSTOMER",
            "CUSTOMER",
            "customer_id",
            "Unique borrower/customer identifier.",
        ),
        make_record(
            "GDA",
            "GDA.GDA_CUSTOMER_CORE",
            "GDA_CUSTOMER_CORE",
            "cust_id",
            "Governed customer identifier derived from CUSTOMER.customer_id.",
        ),
        make_record(
            "GDA",
            "GDA.GDA_FACILITY_CORE",
            "GDA_FACILITY_CORE",
            "cust_id",
            "Borrower/customer identifier linked to the governed facility.",
        ),
    ]

    phase_used, matches = _run_matching_pipeline(
        request=request,
        index=AnalyticsIndex(records=records, faiss_index=None),
        candidate_positions=list(enumerate(records)),
        candidate_records=records,
    )

    assert phase_used == "phase2_fuzzy"
    assert {match.asset_category for match in matches} == {"MDA", "GDA"}
    assert {match.asset_name for match in matches} == {
        "MDA.CUSTOMER",
        "GDA.GDA_CUSTOMER_CORE",
        "GDA.GDA_FACILITY_CORE",
    }


def test_multiple_gda_value_streams_request_human_selection_and_can_be_filtered():
    request = _build_search_request(
        "customer_id",
        "Unique identifier of customer id",
        "UK",
    )
    matches = [
        make_record(
            "GDA",
            "GDA.GDA_CUSTOMER_CORE",
            "GDA_CUSTOMER_CORE",
            "cust_id",
            "Governed customer identifier.",
        ),
        make_record(
            "GDA",
            "GDA.GDA_FACILITY_CORE",
            "GDA_FACILITY_CORE",
            "cust_id",
            "Borrower/customer identifier.",
        ),
    ]
    _, output_matches = _run_matching_pipeline(
        request=request,
        index=AnalyticsIndex(records=matches, faiss_index=None),
        candidate_positions=list(enumerate(matches)),
        candidate_records=matches,
    )

    response = _build_response(
        request,
        output_matches,
        "phase2_fuzzy",
        AnalyticsRetrievalMetadata(documents_considered=2, region_filtered_documents=2),
    )

    assert response.status == "requires_human_selection"
    assert response.human_in_loop_required is True
    assert response.human_selection_options == [
        "GDA.GDA_CUSTOMER_CORE",
        "GDA.GDA_FACILITY_CORE",
    ]
    assert response.selected_details["preferred_layer"] == "GDA"
    assert response.selected_details["gda_value_streams"] == [
        "GDA.GDA_CUSTOMER_CORE",
        "GDA.GDA_FACILITY_CORE",
    ]
    assert set(response.selected_details["gda_value_stream_details"]) == {
        "GDA.GDA_CUSTOMER_CORE",
        "GDA.GDA_FACILITY_CORE",
    }

    selected_matches = _filter_matches_for_selected_asset(
        output_matches,
        "GDA.GDA_FACILITY_CORE",
    )

    assert len(selected_matches) == 2
    assert selected_matches[0].asset_name == "GDA.GDA_FACILITY_CORE"


def test_exact_gda_matches_are_preferred_before_mda_candidates():
    request = _build_search_request(
        "customer_id",
        "Unique identifier of customer id",
        "UK",
    )
    records = [
        make_record(
            "GDA",
            "GDA.GDA_CUSTOMER_CORE",
            "GDA_CUSTOMER_CORE",
            "customer_id",
            "Governed customer identifier.",
        ),
        make_record(
            "MDA",
            "MDA.CUSTOMER",
            "CUSTOMER",
            "customer_id",
            "Unique borrower/customer identifier.",
        ),
    ]

    phase_used, output_matches = _run_matching_pipeline(
        request=request,
        index=AnalyticsIndex(records=records, faiss_index=None),
        candidate_positions=list(enumerate(records)),
        candidate_records=records,
    )

    assert phase_used == "phase1_exact"
    assert [match.asset_category for match in output_matches] == ["GDA"]
    assert output_matches[0].asset_name == "GDA.GDA_CUSTOMER_CORE"


def test_matching_pipeline_returns_top_three_scored_candidates():
    request = _build_search_request(
        "customer_id",
        "Unique identifier of customer id",
        "UK",
    )
    records = [
        make_record(
            "MDA",
            "MDA.CUSTOMER",
            "CUSTOMER",
            "customer_id",
            "Unique borrower/customer identifier.",
        ),
        make_record(
            "GDA",
            "GDA.GDA_CUSTOMER_CORE",
            "GDA_CUSTOMER_CORE",
            "cust_id",
            "Governed customer identifier.",
        ),
        make_record(
            "GDA",
            "GDA.GDA_FACILITY_CORE",
            "GDA_FACILITY_CORE",
            "cust_id",
            "Borrower/customer identifier linked to the governed facility.",
        ),
        make_record(
            "GDA",
            "GDA.GDA_ACCOUNT_CORE",
            "GDA_ACCOUNT_CORE",
            "cust_id",
            "Customer identifier linked to account.",
        ),
        make_record(
            "GDA",
            "GDA.GDA_RISK_CORE",
            "GDA_RISK_CORE",
            "cust_id",
            "Customer identifier linked to risk reporting.",
        ),
    ]

    phase_used, output_matches = _run_matching_pipeline(
        request=request,
        index=AnalyticsIndex(records=records, faiss_index=None),
        candidate_positions=list(enumerate(records)),
        candidate_records=records,
    )

    assert phase_used == "phase2_fuzzy"
    assert len(output_matches) == 3
    assert output_matches == sorted(output_matches, key=lambda match: match.relevance_score, reverse=True)
    assert all(1 <= match.recommendation_score <= 100 for match in output_matches)
    assert any(match.semantic_score > 0 for match in output_matches if match.match_phase != "phase1_exact")


def test_selected_gda_asset_alias_returns_that_asset_first_with_details():
    request = _build_search_request(
        "customer_id",
        "Unique identifier of customer id",
        "UK",
        "GDA.Facility_core",
    )
    records = [
        make_record(
            "MDA",
            "MDA.CUSTOMER",
            "CUSTOMER",
            "customer_id",
            "Unique borrower/customer identifier.",
        ),
        make_record(
            "GDA",
            "GDA.GDA_CUSTOMER_CORE",
            "GDA_CUSTOMER_CORE",
            "cust_id",
            "Governed customer identifier.",
        ),
        make_record(
            "GDA",
            "GDA.GDA_FACILITY_CORE",
            "GDA_FACILITY_CORE",
            "cust_id",
            "Borrower/customer identifier linked to the governed facility.",
        ),
    ]

    phase_used, output_matches = _run_matching_pipeline(
        request=request,
        index=AnalyticsIndex(records=records, faiss_index=None),
        candidate_positions=list(enumerate(records)),
        candidate_records=records,
    )
    request.selected_asset_name = _resolve_selected_asset_name(
        output_matches,
        request.selected_asset_name,
    )
    selected_matches = _filter_matches_for_selected_asset(
        output_matches,
        request.selected_asset_name,
    )
    response = _build_response(
        request,
        selected_matches,
        phase_used,
        AnalyticsRetrievalMetadata(documents_considered=3, region_filtered_documents=3),
    )

    assert request.selected_asset_name == "GDA.GDA_FACILITY_CORE"
    assert selected_matches[0].asset_name == "GDA.GDA_FACILITY_CORE"
    assert selected_matches[0].attribute_name == "cust_id"
    assert response.selected_details["selected_gda_value_stream"] == "GDA.GDA_FACILITY_CORE"
    assert response.selected_details["selected_gda_details"][0]["attribute_name"] == "cust_id"
    assert response.relevant_matches[0].asset_name == "GDA.GDA_FACILITY_CORE"
    assert {match.asset_name for match in response.relevant_matches} == {
        "MDA.CUSTOMER",
        "GDA.GDA_CUSTOMER_CORE",
        "GDA.GDA_FACILITY_CORE",
    }


def test_mda_details_are_returned_when_no_gda_matches_exist():
    request = _build_search_request(
        "customer_id",
        "Unique identifier of customer id",
        "UK",
    )
    records = [
        make_record(
            "MDA",
            "MDA.CUSTOMER",
            "CUSTOMER",
            "customer_id",
            "Unique borrower/customer identifier.",
        ),
        make_record(
            "MDA",
            "MDA.FACILITY",
            "FACILITY",
            "customer_id",
            "Borrower/customer identifier linked to the facility.",
        ),
    ]

    phase_used, output_matches = _run_matching_pipeline(
        request=request,
        index=AnalyticsIndex(records=records, faiss_index=None),
        candidate_positions=list(enumerate(records)),
        candidate_records=records,
    )
    response = _build_response(
        request,
        output_matches,
        phase_used,
        AnalyticsRetrievalMetadata(documents_considered=2, region_filtered_documents=2),
    )

    assert response.status == "matched"
    assert response.selected_details["preferred_layer"] == "MDA"
    assert response.selected_details["mda_value_streams"] == ["MDA.CUSTOMER", "MDA.FACILITY"]
    assert set(response.selected_details["mda_value_stream_details"]) == {"MDA.CUSTOMER", "MDA.FACILITY"}
    assert response.selected_details["mda_value_stream_details"]["MDA.CUSTOMER"][0]["attribute_name"] == "customer_id"


def test_selected_details_reports_no_mda_or_gda_data_when_no_matches_exist():
    request = _build_search_request(
        "not_present",
        "Unknown glossary attribute",
        "UK",
    )
    response = _build_response(
        request,
        [],
        "",
        AnalyticsRetrievalMetadata(documents_considered=2, region_filtered_documents=2),
    )

    assert response.status == "no_match"
    assert response.selected_details["preferred_layer"] == ""
    assert response.selected_details["selection_reason"] == "No data is found at MDA or GDA level."
    assert response.selected_details["gda_value_streams"] == []
    assert response.selected_details["mda_value_streams"] == []
