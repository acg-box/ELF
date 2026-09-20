//! Context Pack v1 read-time assembly over recall/debug readbacks.

mod assembly;
mod routing;
mod types;
mod validation;

pub use types::{
	ContextPackActivationPolicy, ContextPackAuthorityLayer, ContextPackBudgetLimits,
	ContextPackDebugOverrides, ContextPackDebugPolicy, ContextPackFreshnessPolicy, ContextPackItem,
	ContextPackLayerSelector, ContextPackRankingPolicy, ContextPackReadProfilePolicy,
	ContextPackRequest, ContextPackRequiredAnchor, ContextPackResponse, ContextPackRoutingTrace,
	ContextPackRoutingTraceEntry,
};

use crate::{ElfService, RecallDebugPanelRequest, Result};

/// Context Pack v1 schema identifier.
pub const ELF_CONTEXT_PACK_SCHEMA_V1: &str = "elf.context_pack/v1";
/// Context Pack routing trace schema identifier.
pub const ELF_CONTEXT_PACK_ROUTING_TRACE_SCHEMA_V1: &str = "elf.context_pack.routing_trace/v1";

const LAYER_MEMORY: &str = "memory_notes";
const LAYER_DOCS: &str = "source_documents";
const LAYER_KNOWLEDGE: &str = "knowledge_pages";
const LAYER_GRAPH: &str = "graph_facts";
const LAYER_DREAMING: &str = "dreaming_proposals";
const PACK_TTL_MINUTES: i64 = 30;
const DEFAULT_CONTEXT_PACK_LIMIT: u32 = 12;
const MAX_CONTEXT_PACK_LIMIT: u32 = 50;

impl ElfService {
	/// Builds a Context Pack as an ephemeral read-time view over current recall layers.
	pub async fn context_pack_build(&self, req: ContextPackRequest) -> Result<ContextPackResponse> {
		validation::validate_context_pack_request(&req)?;

		let routed = routing::route_context_pack(&req);
		let recall = self
			.recall_debug_panel(RecallDebugPanelRequest {
				tenant_id: req.tenant_id.clone(),
				project_id: req.project_id.clone(),
				agent_id: req.agent_id.clone(),
				read_profile: req.read_profile.clone(),
				trace_id: routing::selector_enabled(&routed, LAYER_MEMORY)
					.then_some(req.trace_id)
					.flatten(),
				query: None,
				docs_query: routing::selector_enabled(&routed, LAYER_DOCS)
					.then(|| routed.docs_query.clone())
					.flatten(),
				knowledge_query: routing::selector_enabled(&routed, LAYER_KNOWLEDGE)
					.then(|| routed.knowledge_query.clone())
					.flatten(),
				graph_subject: routing::selector_enabled(&routed, LAYER_GRAPH)
					.then(|| req.graph_subject.clone())
					.flatten(),
				graph_predicate: routing::selector_enabled(&routed, LAYER_GRAPH)
					.then(|| req.graph_predicate.clone())
					.flatten(),
				include_dreaming: Some(
					routing::selector_enabled(&routed, LAYER_DREAMING) && routed.include_dreaming,
				),
				limit: Some(routed.limit),
				allow_project_trace_debug: false,
			})
			.await?;

		Ok(assembly::build_context_pack_response(&req, routed, recall))
	}
}
