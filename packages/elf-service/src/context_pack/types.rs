//! Public Context Pack request and response contracts.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;
use time::OffsetDateTime;
use uuid::Uuid;

use crate::{GraphQueryEntityRef, GraphQueryPredicateRef, RecallTrace};

/// Request payload for a read-time Context Pack.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct ContextPackRequest {
	/// Tenant that owns the readback.
	pub tenant_id: String,
	/// Project that owns the readback.
	pub project_id: String,
	/// Agent requesting the readback.
	pub agent_id: String,
	/// Read profile used for every underlying recall surface.
	pub read_profile: String,
	/// Task description used by automatic routing.
	pub task: String,
	/// Optional caller-provided title.
	pub title: Option<String>,
	/// Optional caller-provided description.
	pub description: Option<String>,
	/// Optional search trace anchor for memory rows.
	pub trace_id: Option<Uuid>,
	/// Shared query used when docs_query or knowledge_query are omitted.
	pub query: Option<String>,
	/// Optional Source Library query.
	pub docs_query: Option<String>,
	/// Optional Knowledge Workspace page query.
	pub knowledge_query: Option<String>,
	/// Optional graph subject selector.
	pub graph_subject: Option<GraphQueryEntityRef>,
	/// Optional graph predicate selector.
	pub graph_predicate: Option<GraphQueryPredicateRef>,
	/// Whether to include Dreaming review queue proposals.
	pub include_dreaming: Option<bool>,
	/// Maximum pack items.
	pub limit: Option<u32>,
	/// Debug/test/admin-only routing overrides.
	pub debug_overrides: Option<ContextPackDebugOverrides>,
}

/// Debug/test/admin-only overrides for automatic routing.
#[derive(Clone, Debug, Default, Deserialize, Serialize)]
pub struct ContextPackDebugOverrides {
	/// Layers to force-enable when their required anchors are present.
	#[serde(default)]
	pub enable_layers: Vec<String>,
	/// Layers to suppress for this pack.
	#[serde(default)]
	pub disable_layers: Vec<String>,
	/// Layers to prioritize after normal eligibility checks.
	#[serde(default)]
	pub pin_layers: Vec<String>,
}

/// Read-time Context Pack response.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackResponse {
	/// Response schema identifier.
	pub schema: String,
	/// Schema version.
	pub version: u32,
	/// Ephemeral pack identifier.
	pub pack_id: Uuid,
	#[serde(with = "crate::time_serde")]
	/// Pack generation timestamp.
	pub generated_at: OffsetDateTime,
	#[serde(with = "crate::time_serde")]
	/// Pack expiration timestamp.
	pub expires_at: OffsetDateTime,
	/// Pack title.
	pub title: String,
	/// Pack description.
	pub description: String,
	/// Automatic activation policy and override boundaries.
	pub activation_policy: ContextPackActivationPolicy,
	/// Authority layers considered by this pack.
	pub authority_layers: Vec<ContextPackAuthorityLayer>,
	/// Typed selectors per layer.
	pub typed_selectors: BTreeMap<String, ContextPackLayerSelector>,
	/// Required anchors and whether they were supplied.
	pub required_anchors: Vec<ContextPackRequiredAnchor>,
	/// Read-profile policy applied by underlying recall surfaces.
	pub read_profile_policy: ContextPackReadProfilePolicy,
	/// Freshness policy applied to pack items.
	pub freshness_policy: ContextPackFreshnessPolicy,
	/// Budget limits for the pack.
	pub budget_limits: ContextPackBudgetLimits,
	/// Ranking policy for item ordering.
	pub ranking_policy: ContextPackRankingPolicy,
	/// Debug and privacy policy.
	pub debug_policy: ContextPackDebugPolicy,
	/// Activation and selection trace.
	pub routing_trace: ContextPackRoutingTrace,
	/// Bounded eligible context item references.
	pub items: Vec<ContextPackItem>,
	/// Underlying recall trace after scope and freshness gates.
	pub recall_trace: RecallTrace,
}

/// Automatic activation policy metadata.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackActivationPolicy {
	/// Policy schema identifier.
	pub schema: String,
	/// Routing mode.
	pub mode: String,
	/// Whether manual overrides were supplied.
	pub manual_override_present: bool,
	/// Override boundary.
	pub override_policy: String,
}

/// Authority layer metadata.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackAuthorityLayer {
	/// Layer identifier.
	pub layer: String,
	/// Authority class for the layer.
	pub authority_state: String,
	/// Whether selected rows from this layer can become pack items.
	pub eligible_for_pack_items: bool,
}

/// Layer selector state.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackLayerSelector {
	/// Layer identifier.
	pub layer: String,
	/// Selector state.
	pub state: String,
	/// Selector kind.
	pub selector_type: String,
	/// Selector payload.
	pub selector: Value,
	/// Reason code.
	pub reason_code: String,
	/// Whether this selector was affected by a manual override.
	pub manual_override: bool,
	/// Whether this layer was pinned for priority.
	pub pinned: bool,
}

/// Required anchor state.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackRequiredAnchor {
	/// Layer identifier.
	pub layer: String,
	/// Required anchor name.
	pub anchor: String,
	/// Whether the anchor was supplied.
	pub supplied: bool,
	/// Reason code for missing or present state.
	pub reason_code: String,
}

/// Read-profile policy metadata.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackReadProfilePolicy {
	/// Read profile used for all layers.
	pub read_profile: String,
	/// Privacy boundary.
	pub boundary: String,
	/// Scope behavior.
	pub scope_policy: String,
}

/// Freshness policy metadata.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackFreshnessPolicy {
	/// Current-source requirement.
	pub current_only: bool,
	/// Suppressed freshness states.
	pub suppressed_states: Vec<String>,
	/// Redaction behavior.
	pub redaction_policy: String,
}

/// Pack budget limits.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackBudgetLimits {
	/// Maximum returned items.
	pub max_items: u32,
	/// Maximum rows requested per recall layer.
	pub per_layer_recall_limit: u32,
}

/// Pack ranking policy.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackRankingPolicy {
	/// Ranking schema identifier.
	pub schema: String,
	/// Priority behavior.
	pub priority_policy: String,
	/// Whether pinning can bypass eligibility.
	pub pin_bypasses_eligibility: bool,
}

/// Pack debug policy.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackDebugPolicy {
	/// Debug schema identifier.
	pub schema: String,
	/// Whether activation trace is included.
	pub activation_trace: bool,
	/// Source-ref privacy policy.
	pub source_ref_policy: String,
	/// Unreadable evidence policy.
	pub unreadable_policy: String,
}

/// Context Pack routing trace.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackRoutingTrace {
	/// Trace schema identifier.
	pub schema: String,
	/// Trace entries.
	pub entries: Vec<ContextPackRoutingTraceEntry>,
	/// Selected layer count.
	pub selected_count: usize,
	/// Suppressed layer count.
	pub suppressed_count: usize,
	/// Blocked layer count.
	pub blocked_count: usize,
	/// Not-requested layer count.
	pub not_requested_count: usize,
	/// Pinned layers that remained ineligible.
	pub pinned_ineligible_count: usize,
}

/// One routing trace entry.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackRoutingTraceEntry {
	/// Layer identifier.
	pub layer: String,
	/// Activation state.
	pub activation_state: String,
	/// Reason code.
	pub reason_code: String,
	/// Human-readable policy reason.
	pub policy_reason: String,
	/// Whether a manual override affected the layer.
	pub manual_override: bool,
	/// Whether the layer was pinned.
	pub pinned: bool,
	/// Privacy note.
	pub privacy: String,
}

/// One item reference in the Context Pack.
#[derive(Clone, Debug, Serialize)]
pub struct ContextPackItem {
	/// Source layer.
	pub layer: String,
	/// Authority layer.
	pub authority_layer: String,
	/// Freshness state.
	pub freshness_state: String,
	/// Item reference.
	pub item_ref: Value,
	/// Source refs for current readable evidence only.
	pub source_refs: Value,
	/// Score if available.
	pub score: Option<f32>,
	/// Rank if available.
	pub rank: Option<u32>,
	/// Selection or routing reason.
	pub reason_code: String,
	/// Whether pinning raised this item's priority.
	pub pinned_priority: bool,
}
