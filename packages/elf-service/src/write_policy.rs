use elf_domain::writegate::RejectCode;

pub(crate) fn writegate_reason_code(code: RejectCode) -> &'static str {
	match code {
		RejectCode::RejectInvalidText => "REJECT_INVALID_TEXT",
		RejectCode::RejectTooLong => "REJECT_TOO_LONG",
		RejectCode::RejectSecret => "REJECT_SECRET",
		RejectCode::RejectInvalidType => "REJECT_INVALID_TYPE",
		RejectCode::RejectScopeDenied => "REJECT_SCOPE_DENIED",
		RejectCode::RejectEmpty => "REJECT_EMPTY",
	}
}
