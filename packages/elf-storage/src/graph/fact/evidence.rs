use crate::graph::{PgConnection, Result, Uuid};

/// Attach a validated verbatim quote to an existing fact/note evidence link.
pub async fn set_evidence_quote(
	executor: &mut PgConnection,
	fact_id: Uuid,
	note_id: Uuid,
	quote: &str,
) -> Result<()> {
	sqlx::query("UPDATE graph_fact_evidence SET quote=$3 WHERE fact_id=$1 AND note_id=$2")
		.bind(fact_id)
		.bind(note_id)
		.bind(quote)
		.execute(executor)
		.await?;

	Ok(())
}

/// Fetch quotes only for fact/note pairs that the service has already authorized.
pub async fn fetch_evidence_quotes(
	executor: &mut PgConnection,
	pairs: &[(Uuid, Uuid)],
) -> Result<Vec<(Uuid, Uuid, String)>> {
	let (facts, notes): (Vec<_>, Vec<_>) = pairs.iter().copied().unzip();

	Ok(sqlx::query_as("SELECT e.fact_id,e.note_id,e.quote FROM graph_fact_evidence e JOIN unnest($1::uuid[],$2::uuid[]) AS visible(fact_id,note_id) USING(fact_id,note_id) WHERE e.quote IS NOT NULL ORDER BY e.fact_id,e.note_id")
        .bind(facts).bind(notes).fetch_all(executor).await?)
}
