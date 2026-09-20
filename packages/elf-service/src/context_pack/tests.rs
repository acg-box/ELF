use serde_json::Value;

use crate::{
	Error, GraphQueryEntityRef, RecallDebugLayer, RecallDebugRow,
	context_pack::{
		ContextPackDebugOverrides, ContextPackRequest, LAYER_DOCS, LAYER_DREAMING, LAYER_GRAPH,
		LAYER_KNOWLEDGE, LAYER_MEMORY, routing, validation,
	},
};

fn base_request() -> ContextPackRequest {
	ContextPackRequest {
		tenant_id: "tenant".to_string(),
		project_id: "project".to_string(),
		agent_id: "agent".to_string(),
		read_profile: "private_plus_project".to_string(),
		task: "Find current source-backed decisions for routing work.".to_string(),
		title: None,
		description: None,
		trace_id: None,
		query: None,
		docs_query: None,
		knowledge_query: None,
		graph_subject: None,
		graph_predicate: None,
		include_dreaming: None,
		limit: Some(5),
		debug_overrides: None,
	}
}

fn row(
	layer: &str,
	selection_state: &str,
	freshness_state: &str,
	source_refs: Value,
) -> RecallDebugRow {
	RecallDebugRow {
		layer: layer.to_string(),
		item_ref: serde_json::json!({"id": layer}),
		selection_state: selection_state.to_string(),
		authority_layer: layer.to_string(),
		freshness_state: freshness_state.to_string(),
		source_refs,
		score: Some(0.7),
		rank: Some(1),
		rationale: Some("test row".to_string()),
		stage_reason: Some("test_stage".to_string()),
		replay_command: None,
		evidence_class: "pass".to_string(),
		debug_artifacts: serde_json::json!({}),
	}
}

#[test]
fn automatic_routing_activates_query_layers_and_schema_fields() {
	let routed = routing::route_context_pack(&base_request());

	assert_eq!(routed.selectors[LAYER_DOCS].state, "selected");
	assert_eq!(routed.selectors[LAYER_KNOWLEDGE].state, "selected");
	assert_eq!(routed.selectors[LAYER_MEMORY].state, "not_requested");
	assert_eq!(routed.limit, 5);
	assert!(routed.required_anchors.iter().any(|anchor| {
		anchor.layer == LAYER_DOCS && anchor.anchor == "docs_query" && anchor.supplied
	}));
}

#[test]
fn manual_disable_suppresses_layer_without_removing_other_automatic_routes() {
	let mut req = base_request();

	req.debug_overrides = Some(ContextPackDebugOverrides {
		disable_layers: vec![LAYER_DOCS.to_string()],
		..ContextPackDebugOverrides::default()
	});

	let routed = routing::route_context_pack(&req);

	assert_eq!(routed.selectors[LAYER_DOCS].state, "suppressed");
	assert_eq!(routed.selectors[LAYER_DOCS].reason_code, "MANUAL_DISABLED");
	assert_eq!(routed.selectors[LAYER_KNOWLEDGE].state, "selected");
}

#[test]
fn pinned_missing_anchor_is_ineligible_and_cannot_bypass_requirements() {
	let mut req = base_request();

	req.debug_overrides = Some(ContextPackDebugOverrides {
		pin_layers: vec![LAYER_MEMORY.to_string()],
		..ContextPackDebugOverrides::default()
	});

	let routed = routing::route_context_pack(&req);

	assert_eq!(routed.selectors[LAYER_MEMORY].state, "suppressed");
	assert_eq!(
		routed.selectors[LAYER_MEMORY].reason_code,
		"PINNED_OR_ENABLED_MISSING_REQUIRED_ANCHOR"
	);
	assert!(routed.selectors[LAYER_MEMORY].pinned);
}

#[test]
fn pack_items_filter_unreadable_empty_source_refs_and_stale_or_deleted_rows() {
	let rows = vec![
		row(LAYER_DOCS, "selected", "active", serde_json::json!([{"schema": "source_ref/v1"}])),
		row(LAYER_DOCS, "selected", "deleted", serde_json::json!([{"schema": "source_ref/v1"}])),
		row(LAYER_DOCS, "selected", "deprecated", serde_json::json!([{"schema": "source_ref/v1"}])),
		row(LAYER_DOCS, "selected", "active", serde_json::json!([])),
		row(LAYER_KNOWLEDGE, "selected", "active", serde_json::json!({"source_refs": []})),
		row(LAYER_DOCS, "dropped", "active", serde_json::json!([{"schema": "source_ref/v1"}])),
	];
	let layer = RecallDebugLayer {
		layer: LAYER_DOCS.to_string(),
		evidence_class: "pass".to_string(),
		summary: "docs".to_string(),
		anchor: Some("query".to_string()),
		row_count: rows.len(),
		selected_count: 4,
		dropped_count: 1,
		available_count: 0,
		raw_sql_needed: false,
		replayable: false,
		debug_artifacts: serde_json::json!({}),
		rows,
	};
	let routed = routing::route_context_pack(&base_request());
	let items = super::pack_items(&[layer], &routed);

	assert_eq!(items.len(), 1);
	assert_eq!(items[0].freshness_state, "active");
}

#[test]
fn graph_pack_items_accept_evidence_note_ids_and_suppress_non_current_facts() {
	let rows = vec![
		row(
			LAYER_GRAPH,
			"available",
			"current",
			serde_json::json!({"evidence_note_ids": ["note-current"]}),
		),
		row(
			LAYER_GRAPH,
			"available",
			"historical",
			serde_json::json!({"evidence_note_ids": ["note-historical"]}),
		),
		row(
			LAYER_GRAPH,
			"available",
			"future",
			serde_json::json!({"evidence_note_ids": ["note-future"]}),
		),
		row(LAYER_GRAPH, "available", "current", serde_json::json!({"evidence_note_ids": []})),
	];
	let layer = RecallDebugLayer {
		layer: LAYER_GRAPH.to_string(),
		evidence_class: "pass".to_string(),
		summary: "graph".to_string(),
		anchor: Some("entity".to_string()),
		row_count: rows.len(),
		selected_count: 0,
		dropped_count: 0,
		available_count: rows.len(),
		raw_sql_needed: false,
		replayable: false,
		debug_artifacts: serde_json::json!({}),
		rows,
	};
	let routed = routing::route_context_pack(&base_request());
	let items = super::pack_items(&[layer], &routed);

	assert_eq!(items.len(), 1);
	assert_eq!(items[0].layer, LAYER_GRAPH);
	assert_eq!(items[0].freshness_state, "current");
}

#[test]
fn dreaming_pack_items_only_include_active_review_states() {
	let rows = vec![
		row(
			LAYER_DREAMING,
			"reviewable",
			"proposed",
			serde_json::json!({"source_refs": [{"schema": "source_ref/v1"}]}),
		),
		row(
			LAYER_DREAMING,
			"reviewable",
			"approved",
			serde_json::json!({"source_refs": [{"schema": "source_ref/v1"}]}),
		),
		row(
			LAYER_DREAMING,
			"reviewable",
			"rejected",
			serde_json::json!({"source_refs": [{"schema": "source_ref/v1"}]}),
		),
		row(
			LAYER_DREAMING,
			"reviewable",
			"applied",
			serde_json::json!({"source_refs": [{"schema": "source_ref/v1"}]}),
		),
		row(
			LAYER_DREAMING,
			"reviewable",
			"archived",
			serde_json::json!({"source_refs": [{"schema": "source_ref/v1"}]}),
		),
	];
	let layer = RecallDebugLayer {
		layer: LAYER_DREAMING.to_string(),
		evidence_class: "pass".to_string(),
		summary: "dreaming".to_string(),
		anchor: None,
		row_count: rows.len(),
		selected_count: 0,
		dropped_count: 0,
		available_count: 0,
		raw_sql_needed: false,
		replayable: false,
		debug_artifacts: serde_json::json!({}),
		rows,
	};
	let routed = routing::route_context_pack(&base_request());
	let items = super::pack_items(&[layer], &routed);

	assert_eq!(items.len(), 2);
	assert!(items.iter().any(|item| item.freshness_state == "proposed"));
	assert!(items.iter().any(|item| item.freshness_state == "approved"));
}

#[test]
fn validation_rejects_empty_or_non_english_task_and_query() {
	let mut req = base_request();

	req.task = "   ".to_string();

	assert!(matches!(
		validation::validate_context_pack_request(&req),
		Err(Error::InvalidRequest { .. })
	));

	req.task = "Find current source-backed decisions.".to_string();
	req.query = Some("決定".to_string());

	assert!(matches!(
		validation::validate_context_pack_request(&req),
		Err(Error::NonEnglishInput { field }) if field == "$.query"
	));

	req.query = None;
	req.title = Some("決定".to_string());

	assert!(matches!(
		validation::validate_context_pack_request(&req),
		Err(Error::NonEnglishInput { field }) if field == "$.title"
	));

	req.title = None;
	req.graph_subject = Some(GraphQueryEntityRef::Surface { surface: "決定".to_string() });

	assert!(matches!(
		validation::validate_context_pack_request(&req),
		Err(Error::NonEnglishInput { field }) if field == "$.graph_subject.surface"
	));
}

#[test]
fn disabled_layer_rows_are_suppressed_even_when_readable() {
	let mut req = base_request();

	req.debug_overrides = Some(ContextPackDebugOverrides {
		disable_layers: vec![LAYER_DOCS.to_string()],
		..ContextPackDebugOverrides::default()
	});

	let routed = routing::route_context_pack(&req);
	let layer = RecallDebugLayer {
		layer: LAYER_DOCS.to_string(),
		evidence_class: "pass".to_string(),
		summary: "docs".to_string(),
		anchor: Some("query".to_string()),
		row_count: 1,
		selected_count: 1,
		dropped_count: 0,
		available_count: 0,
		raw_sql_needed: false,
		replayable: false,
		debug_artifacts: serde_json::json!({}),
		rows: vec![row(
			LAYER_DOCS,
			"selected",
			"active",
			serde_json::json!([{"schema": "source_ref/v1"}]),
		)],
	};

	assert!(super::pack_items(&[layer], &routed).is_empty());
}

#[test]
fn routing_trace_does_not_disclose_suppressed_layer_counts_or_refs() {
	let mut req = base_request();

	req.debug_overrides = Some(ContextPackDebugOverrides {
		pin_layers: vec![LAYER_MEMORY.to_string()],
		..ContextPackDebugOverrides::default()
	});

	let routed = routing::route_context_pack(&req);
	let trace = super::build_routing_trace(&routed, &[]);
	let memory =
		trace.entries.iter().find(|entry| entry.layer == LAYER_MEMORY).expect("memory trace entry");

	assert_eq!(memory.activation_state, "suppressed");
	assert_eq!(memory.reason_code, "PINNED_OR_ENABLED_MISSING_REQUIRED_ANCHOR");
	assert!(memory.privacy.contains("no unreadable source existence"));
	assert!(!serde_json::to_string(memory).unwrap().contains("source_refs"));
}
