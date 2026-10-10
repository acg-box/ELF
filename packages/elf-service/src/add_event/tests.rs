use crate::add_event::{
	types::{AddEventRequest, EventMessage},
	validation,
};

#[test]
fn accepts_long_french_message_content() {
	let req = AddEventRequest {
			tenant_id: "t".to_string(),
			project_id: "p".to_string(),
			agent_id: "a".to_string(),
			scope: None,
			dry_run: None,
			ingestion_profile: None,
			messages: vec![EventMessage {
				role: "user".to_string(),
					content: "Bonjour, je veux m'assurer que ce texte est suffisamment long et riche en lettres pour declencher la detection de langue. Merci beaucoup."
						.to_string(),
					ts: None,
					msg_id: None,
					write_policy: None,
				}],
			};

	validation::validate_add_event_request(&req).expect("French text must be accepted.");
}
