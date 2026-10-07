"""Deterministic held-out synthetic workloads with a separate evaluator oracle."""

from __future__ import annotations

import hashlib
import random


def opaque(value):
    return "e_" + hashlib.sha256(value.encode()).hexdigest()[:24]


def workload():
    actions, oracle = [], {}

    def write(scope, items):
        actions.append({"action": "ingest", "scope": scope, "items": items})

    def ask(lane, scope, question, facts, evidence=(), forbidden=()):
        case_id = f"case-{len(oracle):03d}"
        actions.append({"action": "query", "scope": scope, "case_id": case_id,
                        "question": question, "lane": lane})
        oracle[case_id] = {"lane": lane, "facts": list(facts),
            "evidence": list(evidence), "forbidden": list(forbidden),
            "supported": bool(facts)}

    for size in (100, 1000):
        scope = f"scale-{size}"
        items = []
        fields = (
            ("production recovery queue", "route"),
            ("signed release channel", "release"),
            ("incident escalation team", "team"),
            ("cache eviction policy", "cache-policy"),
            ("restore verification command", "verify"),
            ("canary deployment ring", "ring"),
            ("billing export bucket", "bucket"),
            ("audit retention policy", "retention-policy"),
        )
        for i in range(size):
            token = hashlib.sha256(f"route:{i}:full-v1".encode()).hexdigest()[:12]
            field, prefix = fields[i % len(fields)]
            items.append({"evidence_id": opaque(f"scale:{size}:{i}"), "text":
                f"Service Aster-{i:04d} approved operations record. Its {field} "
                f"is {prefix}-{token}. The runtime group owns this decision. "
                f"Its development-only alternative is dev-{i:04d}; that alternative is not approved for production."})
        random.Random(20261007).shuffle(items)
        write(scope, items)
        last_audit = size - 1 - ((size - 1 - 7) % 8)
        for i in (0, 9, 18, 27, 44, 53, 62, last_audit):
            token = hashlib.sha256(f"route:{i}:full-v1".encode()).hexdigest()[:12]
            field, prefix = fields[i % len(fields)]
            ask("corpus_scale", scope, f"What is the approved {field} for Aster-{i:04d}?",
                [f"{prefix}-{token}"], [opaque(f"scale:{size}:{i}")], [f"dev-{i:04d}"])
        for i in range(2):
            ask("corpus_scale_absent", scope,
                f"What is Aster-{i:04d}'s signed customer launch date?", [])

    items = [{"evidence_id": opaque(f"session:{i}"), "text":
        f"Session A decision: Boreal-{i} must use handoff-{hashlib.sha256(str(i).encode()).hexdigest()[:10]} "
        "as the next migration checkpoint. This decision is approved and must remain available in future sessions."}
        for i in range(6)]
    write("session", items)
    for i, item in enumerate(items):
        ask("cross_session", "session", f"What migration checkpoint did we approve for Boreal-{i} in the earlier session?",
            [f"handoff-{hashlib.sha256(str(i).encode()).hexdigest()[:10]}"], [item["evidence_id"]])

    items = []
    for i in range(6):
        items += [
            {"evidence_id": opaque(f"authority:{i}:signed"), "text":
             f"Cinder-{i} signed security policy, authority priority 1: recovery uses approved-{i}-amber. "
             "Signed security policies override informal chat even when that chat is newer."},
            {"evidence_id": opaque(f"authority:{i}:chat"), "text":
             f"Cinder-{i} newer informal chat, authority priority 3: someone suggested draft-{i}-violet "
             "for recovery. This suggestion is not an approved policy."},
            {"evidence_id": opaque(f"temporal:{i}:old"), "text":
             f"Dune-{i} approved recovery queue on 2026-08-01 was retired-{i}-blue."},
            {"evidence_id": opaque(f"temporal:{i}:new"), "text":
             f"Dune-{i} approved correction on 2026-09-30: recovery now uses current-{i}-green. "
             f"This correction supersedes retired-{i}-blue from 2026-08-01."},
        ]
    random.Random(27).shuffle(items)
    write("conflicts", items)
    for i in range(6):
        ask("authority", "conflicts", f"Which recovery destination is authorized for Cinder-{i}?",
            [f"approved-{i}-amber"], [opaque(f"authority:{i}:signed")], [f"draft-{i}-violet"])
        ask("temporal", "conflicts", f"Which recovery queue is currently approved for Dune-{i}?",
            [f"current-{i}-green"], [opaque(f"temporal:{i}:new")], [f"retired-{i}-blue"])

    # Both native namespaces are populated before either is queried.
    for scope in ("scope-a", "scope-b"):
        write(scope, [{"evidence_id": opaque(f"{scope}:{i}"), "text":
            f"Ember-{i} private routing record: its secret recovery canary is canary-{scope}-{i}-7fd31. "
            "This record is confined to its native namespace."} for i in range(6)])
    for scope, other in (("scope-a", "scope-b"), ("scope-b", "scope-a")):
        for i in range(6):
            ask("native_scope", scope, f"What is Ember-{i}'s secret recovery canary?",
                [f"canary-{scope}-{i}-7fd31"], [opaque(f"{scope}:{i}")],
                [f"canary-{other}-{j}-7fd31" for j in range(6)])

    items = [{"evidence_id": opaque(f"mutation:{i}"), "text":
        f"Flint-{i} recovery destination is previous-{i}-red."} for i in range(6)]
    write("mutations", items)
    for i in range(6):
        actions.append({"action": "update", "scope": "mutations",
            "evidence_id": opaque(f"mutation:{i}"),
            "text": f"Flint-{i} recovery destination is replaced-{i}-gold."})
    for i in range(6):
        ask("update_restart", "mutations", f"What is Flint-{i}'s recovery destination?",
            [f"replaced-{i}-gold"], [opaque(f"mutation:{i}")], [f"previous-{i}-red"])
    for i in range(6):
        actions.append({"action": "delete", "scope": "mutations", "evidence_id": opaque(f"mutation:{i}")})
    for i in range(6):
        ask("delete_restart", "mutations", f"What is Flint-{i}'s recovery destination?",
            [], [], [f"previous-{i}-red", f"replaced-{i}-gold"])
    return {"schema": "elf.deep_workload/v2", "actions": actions}, oracle
