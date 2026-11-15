"""Strict public explanations and claim-bound private drafts; no model/network calls."""

import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    context_id: str = Field(min_length=1, max_length=160)
    source_id: str = Field(min_length=1, max_length=160)
    quote: str = Field(min_length=12, max_length=500)


class Explanation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["generated", "insufficient_evidence"]
    answer: str = Field(max_length=2500)
    citations: list[Citation] = Field(max_length=5)
    limitations: list[Annotated[str, Field(min_length=1, max_length=600)]] = Field(max_length=5)


class RejectionCode(StrEnum):
    MISSING_CLAIMS = "missing_claims"
    CLAIM_CONTAINS_MARKERS = "claim_contains_markers"
    REFUSAL_CONTAINS_CONTENT = "refusal_contains_content"
    MISSING_ANSWER = "missing_answer"
    MISSING_CITATIONS = "missing_citations"
    MISSING_LIMITATIONS = "missing_limitations"
    UNKNOWN_CONTEXT = "unknown_context"
    SOURCE_NOT_IN_CONTEXT = "source_not_in_context"
    QUOTE_NOT_EXACT = "quote_not_exact"
    CITATION_MARKER_MISSING = "citation_marker_missing"
    UNKNOWN_CITATION_MARKER = "unknown_citation_marker"
    UNSEEN_NUMERIC_TOKEN = "unseen_numeric_token"
    MODEL_SUPPLIED_URL = "model_supplied_url"
    OVERSIZED_LIMITATION = "oversized_limitation"
    INVALID_OUTPUT_SCHEMA = "invalid_output_schema"
    UNEXPECTED_VALIDATION_ERROR = "unexpected_validation_error"


class ExplanationRejected(ValueError):
    def __init__(self, code: RejectionCode):
        self.code = RejectionCode(code)
        super().__init__(self.code.value)


def validate_explanation(result: Explanation, context: list[dict]) -> None:
    if result.status == "insufficient_evidence":
        if result.answer or result.citations:
            raise ExplanationRejected(RejectionCode.REFUSAL_CONTAINS_CONTENT)
        return
    if not result.answer.strip():
        raise ExplanationRejected(RejectionCode.MISSING_ANSWER)
    if not result.citations:
        raise ExplanationRejected(RejectionCode.MISSING_CITATIONS)
    if not result.limitations:
        raise ExplanationRejected(RejectionCode.MISSING_LIMITATIONS)
    by_id = {c["id"]: c for c in context}
    evidence_text = ""
    for citation in result.citations:
        if citation.context_id not in by_id:
            raise ExplanationRejected(RejectionCode.UNKNOWN_CONTEXT)
        item = by_id[citation.context_id]
        if citation.source_id not in item["source_ids"]:
            raise ExplanationRejected(RejectionCode.SOURCE_NOT_IN_CONTEXT)
        if citation.quote not in item["support_text"]:
            raise ExplanationRejected(RejectionCode.QUOTE_NOT_EXACT)
        if f"[{citation.context_id}]" not in result.answer:
            raise ExplanationRejected(RejectionCode.CITATION_MARKER_MISSING)
        evidence_text += " " + item["support_text"]
    cited_ids = {c.context_id for c in result.citations}
    if any(marker not in cited_ids for marker in re.findall(r"\[([^\]]+)\]", result.answer)):
        raise ExplanationRejected(RejectionCode.UNKNOWN_CITATION_MARKER)
    answer = result.answer
    for identifier in by_id:
        answer = answer.replace(identifier, "")
    numbers = r"(?<![\w])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"
    allowed = set(re.findall(numbers, evidence_text))
    if not set(re.findall(numbers, answer)).issubset(allowed):
        raise ExplanationRejected(RejectionCode.UNSEEN_NUMERIC_TOKEN)
    if re.search(r"https?://|www\.", result.answer, re.I):
        raise ExplanationRejected(RejectionCode.MODEL_SUPPLIED_URL)
    if any(len(note) > 600 for note in result.limitations):
        raise ExplanationRejected(RejectionCode.OVERSIZED_LIMITATION)


class SupportedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(
        min_length=1,
        max_length=300,
        description="One short supported English claim. No square brackets, citation markers or URLs; the server renders the marker from citation.context_id.",
    )
    citation: Citation = Field(
        description="The one supplied context item and attached source supporting this claim, with an exact support_text excerpt.",
    )


class ExplanationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["generated", "insufficient_evidence"]
    claims: list[SupportedClaim] = Field(
        max_length=5,
        description="For generated, one to five claims, each with its own citation. For insufficient_evidence, an empty list.",
    )
    limitations: list[Annotated[str, Field(min_length=1, max_length=600)]] = Field(max_length=5)


def render_draft(draft: ExplanationDraft, context: list[dict]) -> Explanation:
    if draft.status == "insufficient_evidence":
        if draft.claims:
            raise ExplanationRejected(RejectionCode.REFUSAL_CONTAINS_CONTENT)
        return Explanation(status=draft.status, answer="", citations=[], limitations=draft.limitations)
    if not draft.claims:
        raise ExplanationRejected(RejectionCode.MISSING_CLAIMS)
    paragraphs: list[str] = []
    citations: list[Citation] = []
    seen: set[tuple[str, str, str]] = set()
    for claim in draft.claims:
        text = claim.text.strip()
        if not text:
            raise ExplanationRejected(RejectionCode.MISSING_ANSWER)
        if "[" in text or "]" in text:
            raise ExplanationRejected(RejectionCode.CLAIM_CONTAINS_MARKERS)
        paragraph = f"{text} [{claim.citation.context_id}]"
        # Validate numbers, quote/source membership and URLs against THIS claim's
        # cited context before rendering the complete answer.
        single = Explanation(
            status="generated",
            answer=paragraph,
            citations=[claim.citation],
            limitations=draft.limitations,
        )
        validate_explanation(single, context)
        paragraphs.append(paragraph)
        key = (claim.citation.context_id, claim.citation.source_id, claim.citation.quote)
        if key not in seen:
            seen.add(key)
            citations.append(claim.citation)
    result = Explanation(
        status="generated",
        answer="\n\n".join(paragraphs),
        citations=citations,
        limitations=draft.limitations,
    )
    validate_explanation(result, context)
    return result
