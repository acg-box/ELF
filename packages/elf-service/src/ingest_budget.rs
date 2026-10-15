use serde::Serialize;

use crate::{Error, Result};

pub(crate) const DEFERRED_INGEST_BUDGET: &str = "DEFERRED_INGEST_BUDGET";

/// One request shares this allowance across extraction input and complete candidates.
pub(crate) struct IngestBudget {
	remaining: usize,
}
impl IngestBudget {
	pub(crate) fn new(bytes: u32) -> Self {
		Self { remaining: bytes as usize }
	}

	pub(crate) fn take(&mut self, value: &impl Serialize) -> Result<bool> {
		let bytes = serde_json::to_vec(value).map_err(|error| Error::InvalidRequest {
			message: format!("Cannot measure ingestion payload: {error}"),
		})?;

		if bytes.len() > self.remaining {
			return Ok(false);
		}

		self.remaining -= bytes.len();

		Ok(true)
	}
}
