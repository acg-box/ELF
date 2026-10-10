"""Build the exact reader input with optional native source boundaries."""


def reader_context(contexts, source_labels=False):
    parts = []
    for index, context in enumerate(contexts):
        label = ''
        if source_labels:
            source = context.get('evidence_id')
            parents = context.get('source_evidence_ids') or []
            label = (f'[Source: {source}]\n' if source else
                     '[Derived from sources: ' + ', '.join(parents) + ']\n' if parents else
                     f'[Source identity unavailable; passage {index + 1}]\n')
        parts.append(label + context['text'])
    return '\n'.join(parts)[:12000]
