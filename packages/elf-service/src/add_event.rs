//! Event ingestion APIs.

mod audit;
mod materialize;
mod persistence;
mod policy;
mod rejection;
mod service;
mod source_ref;
mod types;
mod validation;

pub use types::{AddEventRequest, AddEventResponse, AddEventResult, EventMessage};

use serde_json::Value;

pub(crate) fn extraction_schema() -> Value {
	serde_json::json!(schemars::schema_for!(types::ExtractorOutput))
}

#[cfg(test)] mod tests;
