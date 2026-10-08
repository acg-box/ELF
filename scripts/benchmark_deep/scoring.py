"""Separate answer matching from support in the context supplied for that case."""


def score_answer(expected, answer, supplied_context):
    if answer is None:
        return {"correct": None, "answer_matches_expected": None, "fact_in_supplied_context": None}
    matches = (answer["supported"] == expected["supported"] and
        (all(f.casefold() in answer["text"].casefold() for f in expected["facts"])
         if expected["supported"] else answer["text"].strip().casefold() == "unknown"))
    grounded = (all(f.casefold() in supplied_context.casefold() for f in expected["facts"])
                if expected["supported"] else None)
    return {"correct": matches and (grounded if expected["supported"] else True),
            "answer_matches_expected": matches, "fact_in_supplied_context": grounded}
