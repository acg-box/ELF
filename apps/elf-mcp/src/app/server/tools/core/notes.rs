use color_eyre::Result;
use rmcp::{
	ErrorData,
	model::{CallToolResult, JsonObject},
};

use crate::app::server::{
	ElfMcp, HttpMethod,
	schemas::{
		evidence_check_schema, evidence_pack_schema, evidence_recall_schema, notes_get_schema,
		notes_list_schema, notes_patch_schema, notes_publish_schema, notes_unpublish_schema,
	},
	support,
};

#[rmcp::tool_router(router = core_notes_tool_router, vis = "pub(in crate::app::server)")]
impl ElfMcp {
	#[rmcp::tool(name = "elf_evidence_recall", description = "Supplement incomplete recall with 1-4 literal subject names or identifiers. Retrieve original text independently of extraction, plus source-diverse note and incoming/outgoing graph evidence across distinct entity candidates without merging them. Supply as_of for historical questions; compare states effective then, retain late reports, and do not apply later decisions backward. Match and citation validity do not prove truth.", input_schema = evidence_recall_schema())]
	async fn elf_evidence_recall(&self, params: JsonObject) -> Result<CallToolResult, ErrorData> {
		self.forward(HttpMethod::Post, "/v2/evidence/recall", params, None).await
	}

	#[rmcp::tool(
		name = "elf_notes_list",
		description = "List notes in a tenant and project with optional filters.",
		input_schema = notes_list_schema()
	)]
	async fn elf_notes_list(&self, params: JsonObject) -> Result<CallToolResult, ErrorData> {
		self.forward(HttpMethod::Get, "/v2/notes", params, None).await
	}

	#[rmcp::tool(
		name = "elf_notes_get",
		description = "Fetch a single note by note_id.",
		input_schema = notes_get_schema()
	)]
	async fn elf_notes_get(&self, mut params: JsonObject) -> Result<CallToolResult, ErrorData> {
		let note_id = support::take_required_string(&mut params, "note_id")?;
		let path = format!("/v2/notes/{note_id}");

		self.forward(HttpMethod::Get, &path, JsonObject::new(), None).await
	}

	#[rmcp::tool(
        name = "elf_notes_evidence",
        description = "Read a derived note with bounded, hash-verified original context. Use the original subject and time to assess support; a valid source hash does not prove a claim. Does not modify sources.",
        input_schema = notes_get_schema()
    )]
	async fn elf_notes_evidence(
		&self,
		mut params: JsonObject,
	) -> Result<CallToolResult, ErrorData> {
		let note_id = support::take_required_string(&mut params, "note_id")?;

		self.forward(
			HttpMethod::Get,
			&format!("/v2/notes/{note_id}/evidence"),
			JsonObject::new(),
			None,
		)
		.await
	}

	#[rmcp::tool(name = "elf_evidence_pack", description = "Resolve 1-12 retrieved note IDs into deduplicated original context with native citation references. Source timestamps are record times, not inferred fact validity. Incomplete context does not prove absence.", input_schema = evidence_pack_schema())]
	async fn elf_evidence_pack(&self, params: JsonObject) -> Result<CallToolResult, ErrorData> {
		self.forward(HttpMethod::Post, "/v2/evidence/pack", params, None).await
	}

	#[rmcp::tool(name = "elf_evidence_check", description = "Check each claim citation against currently readable notes or hash-guarded original quotes. This verifies source bindings, not semantic entailment.", input_schema = evidence_check_schema())]
	async fn elf_evidence_check(&self, params: JsonObject) -> Result<CallToolResult, ErrorData> {
		self.forward(HttpMethod::Post, "/v2/evidence/check", params, None).await
	}

	#[rmcp::tool(
		name = "elf_notes_patch",
		description = "Patch a note by note_id. Only provided fields are updated.",
		input_schema = notes_patch_schema()
	)]
	async fn elf_notes_patch(&self, mut params: JsonObject) -> Result<CallToolResult, ErrorData> {
		let note_id = support::take_required_string(&mut params, "note_id")?;
		let path = format!("/v2/notes/{note_id}");

		self.forward(HttpMethod::Patch, &path, params, None).await
	}

	#[rmcp::tool(
		name = "elf_notes_delete",
		description = "Delete a note by note_id.",
		input_schema = notes_get_schema()
	)]
	async fn elf_notes_delete(&self, mut params: JsonObject) -> Result<CallToolResult, ErrorData> {
		let note_id = support::take_required_string(&mut params, "note_id")?;
		let path = format!("/v2/notes/{note_id}");

		self.forward(HttpMethod::Delete, &path, JsonObject::new(), None).await
	}

	#[rmcp::tool(
		name = "elf_notes_publish",
		description = "Publish a note from agent_private into a shared space (team_shared or org_shared).",
		input_schema = notes_publish_schema()
	)]
	async fn elf_notes_publish(&self, mut params: JsonObject) -> Result<CallToolResult, ErrorData> {
		let note_id = support::take_required_string(&mut params, "note_id")?;
		let path = format!("/v2/notes/{note_id}/publish");

		self.forward(HttpMethod::Post, &path, params, None).await
	}

	#[rmcp::tool(
		name = "elf_notes_unpublish",
		description = "Unpublish a shared note back into agent_private scope.",
		input_schema = notes_unpublish_schema()
	)]
	async fn elf_notes_unpublish(
		&self,
		mut params: JsonObject,
	) -> Result<CallToolResult, ErrorData> {
		let note_id = support::take_required_string(&mut params, "note_id")?;
		let path = format!("/v2/notes/{note_id}/unpublish");

		self.forward(HttpMethod::Post, &path, params, None).await
	}
}
