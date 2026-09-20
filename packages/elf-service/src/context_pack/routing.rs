//! Select recall layers and enforce anchor and override precedence.

use std::collections::{BTreeMap, BTreeSet};

use serde_json::Value;

use crate::context_pack::{
	ContextPackLayerSelector, ContextPackRequest, ContextPackRequiredAnchor,
	DEFAULT_CONTEXT_PACK_LIMIT, LAYER_DOCS, LAYER_DREAMING, LAYER_GRAPH, LAYER_KNOWLEDGE,
	LAYER_MEMORY, MAX_CONTEXT_PACK_LIMIT,
};

#[derive(Clone, Debug)]
pub(super) struct RoutedPack {
	pub(super) limit: u32,
	pub(super) title: String,
	pub(super) description: String,
	pub(super) docs_query: Option<String>,
	pub(super) knowledge_query: Option<String>,
	pub(super) include_dreaming: bool,
	pub(super) selectors: BTreeMap<String, ContextPackLayerSelector>,
	pub(super) required_anchors: Vec<ContextPackRequiredAnchor>,
	pub(super) disabled_layers: BTreeSet<String>,
	pub(super) pinned_layers: BTreeSet<String>,
}

struct LayerRouteInput<'a> {
	layer: &'a str,
	default_enabled: bool,
	manual_enabled: bool,
	manual_disabled: bool,
	pinned: bool,
	anchor_name: &'a str,
	anchor_supplied: bool,
	selector_type: &'a str,
	selector: Value,
}

struct SelectorSources<'a> {
	req: &'a ContextPackRequest,
	docs_query: &'a Option<String>,
	knowledge_query: &'a Option<String>,
	include_dreaming: bool,
	enabled: &'a BTreeSet<String>,
	disabled: &'a BTreeSet<String>,
	pinned: &'a BTreeSet<String>,
}

pub(super) fn route_context_pack(req: &ContextPackRequest) -> RoutedPack {
	let limit = req.limit.unwrap_or(DEFAULT_CONTEXT_PACK_LIMIT).clamp(1, MAX_CONTEXT_PACK_LIMIT);
	let task = trimmed_opt(Some(req.task.as_str()));
	let base_query = trimmed_opt(req.query.as_deref()).or_else(|| task.clone());
	let docs_query = trimmed_opt(req.docs_query.as_deref()).or_else(|| base_query.clone());
	let knowledge_query =
		trimmed_opt(req.knowledge_query.as_deref()).or_else(|| base_query.clone());
	let include_dreaming = req.include_dreaming == Some(true)
		|| task.as_deref().is_some_and(|value| {
			contains_any(value, &["proposal", "review", "dreaming", "consolidation"])
		});
	let overrides = req.debug_overrides.clone().unwrap_or_default();
	let enabled = normalize_layers(overrides.enable_layers);
	let disabled = normalize_layers(overrides.disable_layers);
	let pinned = normalize_layers(overrides.pin_layers);
	let title = trimmed_opt(req.title.as_deref()).unwrap_or_else(|| "Context Pack".to_string());
	let description = trimmed_opt(req.description.as_deref()).unwrap_or_else(|| {
		"Read-time scoped context assembled from current ELF authority layers.".to_string()
	});
	let (selectors, required_anchors) = route_selectors(SelectorSources {
		req,
		docs_query: &docs_query,
		knowledge_query: &knowledge_query,
		include_dreaming,
		enabled: &enabled,
		disabled: &disabled,
		pinned: &pinned,
	});

	RoutedPack {
		limit,
		title,
		description,
		docs_query,
		knowledge_query,
		include_dreaming: include_dreaming || enabled.contains(LAYER_DREAMING),
		selectors,
		required_anchors,
		disabled_layers: disabled,
		pinned_layers: pinned,
	}
}

pub(super) fn selector_enabled(routed: &RoutedPack, layer: &str) -> bool {
	routed.selectors.get(layer).is_some_and(|selector| selector.state == "selected")
}

fn route_selectors(
	input: SelectorSources<'_>,
) -> (BTreeMap<String, ContextPackLayerSelector>, Vec<ContextPackRequiredAnchor>) {
	let mut selectors = BTreeMap::new();
	let mut required_anchors = Vec::new();

	add_selector(
		&mut selectors,
		&mut required_anchors,
		LayerRouteInput {
			layer: LAYER_MEMORY,
			default_enabled: input.req.trace_id.is_some(),
			manual_enabled: input.enabled.contains(LAYER_MEMORY),
			manual_disabled: input.disabled.contains(LAYER_MEMORY),
			pinned: input.pinned.contains(LAYER_MEMORY),
			anchor_name: "trace_id",
			anchor_supplied: input.req.trace_id.is_some(),
			selector_type: "trace",
			selector: input
				.req
				.trace_id
				.map(|trace_id| serde_json::json!({ "trace_id": trace_id }))
				.unwrap_or_else(|| serde_json::json!({})),
		},
	);
	add_selector(
		&mut selectors,
		&mut required_anchors,
		LayerRouteInput {
			layer: LAYER_DOCS,
			default_enabled: input.docs_query.is_some(),
			manual_enabled: input.enabled.contains(LAYER_DOCS),
			manual_disabled: input.disabled.contains(LAYER_DOCS),
			pinned: input.pinned.contains(LAYER_DOCS),
			anchor_name: "docs_query",
			anchor_supplied: input.docs_query.is_some(),
			selector_type: "query",
			selector: input
				.docs_query
				.as_ref()
				.map(|query| serde_json::json!({ "query": query }))
				.unwrap_or_else(|| serde_json::json!({})),
		},
	);
	add_selector(
		&mut selectors,
		&mut required_anchors,
		LayerRouteInput {
			layer: LAYER_KNOWLEDGE,
			default_enabled: input.knowledge_query.is_some(),
			manual_enabled: input.enabled.contains(LAYER_KNOWLEDGE),
			manual_disabled: input.disabled.contains(LAYER_KNOWLEDGE),
			pinned: input.pinned.contains(LAYER_KNOWLEDGE),
			anchor_name: "knowledge_query",
			anchor_supplied: input.knowledge_query.is_some(),
			selector_type: "query",
			selector: input
				.knowledge_query
				.as_ref()
				.map(|query| serde_json::json!({ "query": query }))
				.unwrap_or_else(|| serde_json::json!({})),
		},
	);
	add_selector(
		&mut selectors,
		&mut required_anchors,
		LayerRouteInput {
			layer: LAYER_GRAPH,
			default_enabled: input.req.graph_subject.is_some(),
			manual_enabled: input.enabled.contains(LAYER_GRAPH),
			manual_disabled: input.disabled.contains(LAYER_GRAPH),
			pinned: input.pinned.contains(LAYER_GRAPH),
			anchor_name: "graph_subject",
			anchor_supplied: input.req.graph_subject.is_some(),
			selector_type: "graph_subject",
			selector: input
				.req
				.graph_subject
				.as_ref()
				.map(|subject| serde_json::json!({ "subject": subject }))
				.unwrap_or_else(|| serde_json::json!({})),
		},
	);
	add_selector(
		&mut selectors,
		&mut required_anchors,
		LayerRouteInput {
			layer: LAYER_DREAMING,
			default_enabled: input.include_dreaming,
			manual_enabled: input.enabled.contains(LAYER_DREAMING),
			manual_disabled: input.disabled.contains(LAYER_DREAMING),
			pinned: input.pinned.contains(LAYER_DREAMING),
			anchor_name: "include_dreaming",
			anchor_supplied: input.include_dreaming || input.enabled.contains(LAYER_DREAMING),
			selector_type: "review_queue",
			selector: serde_json::json!({
				"include_dreaming": input.include_dreaming || input.enabled.contains(LAYER_DREAMING)
			}),
		},
	);

	(selectors, required_anchors)
}

fn add_selector(
	selectors: &mut BTreeMap<String, ContextPackLayerSelector>,
	required_anchors: &mut Vec<ContextPackRequiredAnchor>,
	input: LayerRouteInput<'_>,
) {
	let manual_override = input.manual_enabled || input.manual_disabled || input.pinned;
	let (state, reason_code) = if input.manual_disabled {
		("suppressed", "MANUAL_DISABLED")
	} else if !input.anchor_supplied && (input.manual_enabled || input.pinned) {
		("suppressed", "PINNED_OR_ENABLED_MISSING_REQUIRED_ANCHOR")
	} else if input.default_enabled || input.manual_enabled {
		("selected", "AUTOMATIC_ROUTING_MATCH")
	} else {
		("not_requested", "AUTOMATIC_ROUTING_NO_MATCH")
	};

	required_anchors.push(ContextPackRequiredAnchor {
		layer: input.layer.to_string(),
		anchor: input.anchor_name.to_string(),
		supplied: input.anchor_supplied,
		reason_code: if input.anchor_supplied { "ANCHOR_SUPPLIED" } else { "ANCHOR_MISSING" }
			.to_string(),
	});
	selectors.insert(
		input.layer.to_string(),
		ContextPackLayerSelector {
			layer: input.layer.to_string(),
			state: state.to_string(),
			selector_type: input.selector_type.to_string(),
			selector: input.selector,
			reason_code: reason_code.to_string(),
			manual_override,
			pinned: input.pinned,
		},
	);
}

fn trimmed_opt(value: Option<&str>) -> Option<String> {
	value.map(str::trim).filter(|value| !value.is_empty()).map(str::to_string)
}

fn contains_any(value: &str, needles: &[&str]) -> bool {
	let lower = value.to_ascii_lowercase();

	needles.iter().any(|needle| lower.contains(needle))
}

fn normalize_layers(layers: Vec<String>) -> BTreeSet<String> {
	layers
		.into_iter()
		.filter_map(|layer| {
			let normalized = layer.trim().to_ascii_lowercase().replace('-', "_");

			match normalized.as_str() {
				LAYER_MEMORY | "memory" | "notes" => Some(LAYER_MEMORY.to_string()),
				LAYER_DOCS | "docs" | "documents" | "source" => Some(LAYER_DOCS.to_string()),
				LAYER_KNOWLEDGE | "knowledge" | "pages" => Some(LAYER_KNOWLEDGE.to_string()),
				LAYER_GRAPH | "graph" | "relations" => Some(LAYER_GRAPH.to_string()),
				LAYER_DREAMING | "dreaming" | "proposals" => Some(LAYER_DREAMING.to_string()),
				_ => None,
			}
		})
		.collect()
}
