"""Conversation-local citation handles; native access and hash checks stay in ELF."""
from copy import deepcopy


def compact_check(response):
    # Keep every verdict and dependency slot. Repeating source bodies is unnecessary.
    return {'claims': [{k: v for k, v in claim.items() if k != 'resolved_citations'}
                       for claim in response['claims']],
            'semantic_support': response['semantic_support']}


class EvidenceHandles:
    def __init__(self):
        self.native = {}
        self.visible = set()

    def handle(self, reference):
        for handle, original in self.native.items():
            if original == reference:
                return handle
        handle = 'E' + str(len(self.native) + 1)
        self.native[handle] = reference
        return handle

    def project(self, value):
        value = deepcopy(value)
        def visit(node):
            if isinstance(node, dict):
                ref = node.get('reference')
                if isinstance(ref, str) and ref.startswith('elf-source-v1/'):
                    node['reference'] = self.handle(ref)
                    if node['reference'] in self.visible:
                        # The exact original is still in this conversation. Keep its
                        # handle and provenance; do not charge for its body again.
                        for field in ('text', 'excerpt'):
                            node.pop(field, None)
                        node['already_read'] = True
                if 'source_references' in node:
                    node['source_references'] = [self.handle(ref) for ref in node['source_references']]
                for child in node.values():
                    visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)
        visit(value)
        return value

    def expose(self, value):
        if isinstance(value, dict):
            ref = value.get('reference')
            if ref in self.native:
                self.visible.add(ref)
            for child in value.values():
                self.expose(child)
        elif isinstance(value, list):
            for child in value:
                self.expose(child)

    def resolve(self, claims):
        claims = deepcopy(claims)
        for claim in claims:
            for citation in claim.get('citations', []):
                ref = citation.get('reference')
                if citation.get('kind') != 'reference' or ref not in self.visible:
                    raise ValueError('Use a citation handle from an original already returned in this conversation.')
                citation['reference'] = self.native[ref]
        return claims
