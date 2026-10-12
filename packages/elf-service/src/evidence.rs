//! Read-time evidence expansion and quote binding. No source mutation or semantic oracle.

mod claims;
mod pack;
mod reference;
mod sources;
mod types;

pub use self::{
	pack::{EvidencePackNote, EvidencePackRequest, EvidencePackResponse, EvidencePackSource},
	types::{
		ClaimBinding, ClaimCitation, ClaimEvidence, ClaimState, EvidenceCheckRequest,
		EvidenceCheckResponse, NoteEvidenceResponse, NoteSourceEvidence,
	},
};

use crate::{ElfService, Error, NoteFetchRequest, Result};

const MAX_SOURCES: usize = 4;
const MAX_CLAIMS: usize = 12;
const MAX_CITATIONS: usize = 8;
