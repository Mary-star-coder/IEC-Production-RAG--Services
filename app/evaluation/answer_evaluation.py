
def evaluate_answer(answer, retrieved_chunks, citations, abstained):
    """
    Check answer structure and source availability.

    These checks do not prove semantic faithfulness; generation uses a
    separate grounded prompt and citations identify the supplied sources.
    """

    if abstained:
        checks = {
            "abstention_message_present": (
                "could not find relevant information" in answer.lower()
            ),
            "citations_empty": len(citations) == 0,
        }

        return {
            "passed": all(checks.values()),
            "checks": checks,
            "evaluation_type": "abstention_handling",
        }

    source_texts = [
        chunk.get("text", "").strip()
        for chunk in retrieved_chunks
    ]

    checks = {
        "answer_not_empty": bool(answer.strip()),
        "citations_present": len(citations) > 0,
        "retrieved_sources_present": len(source_texts) > 0,
    }

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "evaluation_type": "answer_completeness",
    }
