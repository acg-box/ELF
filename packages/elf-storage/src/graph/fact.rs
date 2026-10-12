mod evidence;
mod query;
mod supersession;
mod write;

pub use self::{
	evidence::{fetch_evidence_quotes, set_evidence_quote},
	query::fetch_active_facts_for_subject,
	supersession::supersede_conflicting_active_facts,
	write::{insert_fact_with_evidence, upsert_fact_with_evidence},
};
