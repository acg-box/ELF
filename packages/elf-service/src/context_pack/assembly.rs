//! Assemble eligible rows, ranking, and the matching routing trace.

use std::collections::BTreeMap;

use serde_json::Value;
use time::{Duration, OffsetDateTime};
use uuid::Uuid;

use crate::{
	RecallDebugLayer, RecallDebugPanelResponse, RecallDebugRow,
	context_pack::{
		ContextPackActivationPolicy, ContextPackAuthorityLayer, ContextPackBudgetLimits,
		ContextPackDebugPolicy, ContextPackFreshnessPolicy, ContextPackItem,
		ContextPackRankingPolicy, ContextPackReadProfilePolicy, ContextPackRequest,
		ContextPackResponse, ContextPackRoutingTrace, ContextPackRoutingTraceEntry,
		ELF_CONTEXT_PACK_ROUTING_TRACE_SCHEMA_V1, ELF_CONTEXT_PACK_SCHEMA_V1, LAYER_DOCS,
		LAYER_DREAMING, LAYER_GRAPH, LAYER_KNOWLEDGE, LAYER_MEMORY, PACK_TTL_MINUTES,
		routing::RoutedPack,
	},
};

pub(super) fn build_context_pack_response(
	req: &ContextPackRequest,
	routed: RoutedPack,
	recall: RecallDebugPanelResponse,
) -> ContextPackResponse {
	let generated_at = OffsetDateTime::now_utc();
	let mut items = pack_items(&recall.layers, &routed);

	items.truncate(routed.limit as usize);

	let routing_trace = build_routing_trace(&routed, &recall.layers);

	ContextPackResponse {
		schema: ELF_CONTEXT_PACK_SCHEMA_V1.to_string(),
		version: 1,
		pack_id: Uuid::new_v4(),
		generated_at,
		expires_at: generated_at + Duration::minutes(PACK_TTL_MINUTES),
		title: routed.title.clone(),
		description: routed.description.clone(),
		activation_policy: ContextPackActivationPolicy {
			schema: "elf.context_pack.activation_policy/v1".to_string(),
			mode: "automatic".to_string(),
			manual_override_present: req.debug_overrides.is_some(),
			override_policy:
				"manual enable/disable/pin is debug/test/admin-only; pinning changes priority only"
					.to_string(),
		},
		authority_layers: authority_layers(),
		typed_selectors: routed.selectors.clone(),
		required_anchors: routed.required_anchors.clone(),
		read_profile_policy: ContextPackReadProfilePolicy {
			read_profile: req.read_profile.clone(),
			boundary: "all layer reads use the request read_profile and service grants".to_string(),
			scope_policy:
				"agent_private requires owner match; shared scopes require readable grants"
					.to_string(),
		},
		freshness_policy: ContextPackFreshnessPolicy {
			current_only: true,
			suppressed_states: vec![
				"deleted".to_string(),
				"deprecated".to_string(),
				"expired".to_string(),
				"stale".to_string(),
				"superseded".to_string(),
				"tombstoned".to_string(),
			],
			redaction_policy:
				"items include only source refs already returned by readable current recall rows"
					.to_string(),
		},
		budget_limits: ContextPackBudgetLimits {
			max_items: routed.limit,
			per_layer_recall_limit: routed.limit,
		},
		ranking_policy: ContextPackRankingPolicy {
			schema: "elf.context_pack.ranking_policy/v1".to_string(),
			priority_policy:
				"eligible pinned layers sort ahead of unpinned layers, then by rank and score"
					.to_string(),
			pin_bypasses_eligibility: false,
		},
		debug_policy: ContextPackDebugPolicy {
			schema: "elf.context_pack.debug_policy/v1".to_string(),
			activation_trace: true,
			source_ref_policy:
				"debug output omits unreadable/private source existence, counts, refs, and content"
					.to_string(),
			unreadable_policy:
				"unreadable rows are filtered by underlying recall surfaces before pack assembly"
					.to_string(),
		},
		routing_trace,
		items,
		recall_trace: recall.recall_trace,
	}
}

fn authority_layers() -> Vec<ContextPackAuthorityLayer> {
	[
		(LAYER_MEMORY, "authoritative_memory", true),
		(LAYER_DOCS, "source_evidence", true),
		(LAYER_KNOWLEDGE, "derived_knowledge", true),
		(LAYER_GRAPH, "graph_lite_fact", true),
		(LAYER_DREAMING, "reviewable_proposal", true),
	]
	.into_iter()
	.map(|(layer, authority_state, eligible_for_pack_items)| ContextPackAuthorityLayer {
		layer: layer.to_string(),
		authority_state: authority_state.to_string(),
		eligible_for_pack_items,
	})
	.collect()
}

fn build_routing_trace(
	routed: &RoutedPack,
	layers: &[RecallDebugLayer],
) -> ContextPackRoutingTrace {
	let layer_map =
		layers.iter().map(|layer| (layer.layer.as_str(), layer)).collect::<BTreeMap<_, _>>();
	let mut entries = Vec::new();

	for (layer, selector) in &routed.selectors {
		let mut activation_state = selector.state.clone();
		let mut reason_code = selector.reason_code.clone();
		let mut policy_reason = match selector.reason_code.as_str() {
			"MANUAL_DISABLED" => "Layer was suppressed by a debug override.".to_string(),
			"PINNED_OR_ENABLED_MISSING_REQUIRED_ANCHOR" =>
				"Pinned or enabled layer stayed ineligible because a required anchor was missing."
					.to_string(),
			"AUTOMATIC_ROUTING_MATCH" => "Automatic routing selected this layer.".to_string(),
			_ => "Automatic routing did not request this layer.".to_string(),
		};

		if let Some(recall_layer) = layer_map.get(layer.as_str()) {
			if recall_layer.evidence_class == "blocked" {
				activation_state = "blocked".to_string();
				reason_code = "RECALL_LAYER_BLOCKED".to_string();
				policy_reason = recall_layer.summary.clone();
			} else if selector.state == "selected"
				&& recall_layer.rows.iter().all(|row| !row_eligible_for_pack(row))
			{
				activation_state = if selector.pinned {
					"pinned_ineligible".to_string()
				} else {
					"suppressed".to_string()
				};
				reason_code = "NO_CURRENT_READABLE_SELECTED_ROWS".to_string();
				policy_reason =
					"Layer returned no current readable selected, available, or reviewable rows."
						.to_string();
			}
		}

		entries.push(ContextPackRoutingTraceEntry {
			layer: layer.clone(),
			activation_state,
			reason_code,
			policy_reason,
			manual_override: selector.manual_override,
			pinned: selector.pinned,
			privacy: "no unreadable source existence, counts, refs, or content disclosed"
				.to_string(),
		});
	}

	ContextPackRoutingTrace {
		schema: ELF_CONTEXT_PACK_ROUTING_TRACE_SCHEMA_V1.to_string(),
		selected_count: entries.iter().filter(|entry| entry.activation_state == "selected").count(),
		suppressed_count: entries
			.iter()
			.filter(|entry| entry.activation_state == "suppressed")
			.count(),
		blocked_count: entries.iter().filter(|entry| entry.activation_state == "blocked").count(),
		not_requested_count: entries
			.iter()
			.filter(|entry| entry.activation_state == "not_requested")
			.count(),
		pinned_ineligible_count: entries
			.iter()
			.filter(|entry| entry.activation_state == "pinned_ineligible")
			.count(),
		entries,
	}
}

fn pack_items(layers: &[RecallDebugLayer], routed: &RoutedPack) -> Vec<ContextPackItem> {
	let mut items = layers
		.iter()
		.filter(|layer| !routed.disabled_layers.contains(layer.layer.as_str()))
		.flat_map(|layer| {
			layer.rows.iter().filter(|row| row_eligible_for_pack(row)).map(|row| {
				let pinned_priority = routed.pinned_layers.contains(row.layer.as_str());

				ContextPackItem {
					layer: row.layer.clone(),
					authority_layer: row.authority_layer.clone(),
					freshness_state: row.freshness_state.clone(),
					item_ref: row.item_ref.clone(),
					source_refs: row.source_refs.clone(),
					score: row.score,
					rank: row.rank,
					reason_code: row
						.stage_reason
						.clone()
						.or_else(|| row.rationale.clone())
						.unwrap_or_else(|| "selected_by_recall_layer".to_string()),
					pinned_priority,
				}
			})
		})
		.collect::<Vec<_>>();

	items.sort_by(|left, right| {
		right
			.pinned_priority
			.cmp(&left.pinned_priority)
			.then_with(|| left.rank.unwrap_or(u32::MAX).cmp(&right.rank.unwrap_or(u32::MAX)))
			.then_with(|| {
				right
					.score
					.unwrap_or(f32::NEG_INFINITY)
					.total_cmp(&left.score.unwrap_or(f32::NEG_INFINITY))
			})
			.then_with(|| left.layer.cmp(&right.layer))
	});

	items
}

fn row_eligible_for_pack(row: &RecallDebugRow) -> bool {
	matches!(row.selection_state.as_str(), "selected" | "available" | "reviewable")
		&& row.evidence_class == "pass"
		&& layer_freshness_eligible(row.layer.as_str(), row.freshness_state.as_str())
		&& source_refs_present(&row.source_refs)
}

fn layer_freshness_eligible(layer: &str, freshness_state: &str) -> bool {
	if layer == LAYER_DREAMING {
		return matches!(freshness_state, "proposed" | "approved");
	}

	!stale_or_non_current(freshness_state)
}

fn stale_or_non_current(freshness_state: &str) -> bool {
	matches!(
		freshness_state,
		"deleted"
			| "deprecated"
			| "expired"
			| "stale" | "superseded"
			| "tombstoned"
			| "historical"
			| "future"
	)
}

fn source_refs_present(value: &Value) -> bool {
	match value {
		Value::Null => false,
		Value::Array(values) => !values.is_empty(),
		Value::Object(values) =>
			["source_refs", "source_ref", "source_snapshot", "affected_refs", "evidence_note_ids"]
				.iter()
				.filter_map(|key| values.get(*key))
				.any(source_refs_present),
		Value::String(value) => !value.trim().is_empty(),
		_ => true,
	}
}

#[cfg(test)]
#[path = "tests.rs"]
mod tests;
