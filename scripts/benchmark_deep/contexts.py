"""Build the exact reader input with optional native source boundaries."""


def reader_context(contexts, source_labels=False):
    return '\n'.join(
        (f'[Source: {c.get("evidence_id") or "unresolved"}]\n' if source_labels else '') + c['text']
        for c in contexts
    )[:12000]
