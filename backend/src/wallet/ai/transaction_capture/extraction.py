from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any, Protocol

from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

from wallet.ai.llm import StructuredChatModel
from wallet.ai.transaction_capture.domain import UserContribution

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class MentionKind(StrEnum):
    ACTION = "action"
    MONEY = "money"
    DATE_TIME = "date_time"
    REFERENCE = "reference"
    FREE_TEXT = "free_text"
    CHANGE = "change"


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class ExtractedMention:
    id: str
    kind: MentionKind
    evidence: SourceEvidence


@dataclass(frozen=True, slots=True)
class ExtractionIssue:
    kind: MentionKind
    source_text: str
    reason: str


@dataclass(frozen=True, slots=True)
class ContributionExtraction:
    mentions: tuple[ExtractedMention, ...] = ()
    issues: tuple[ExtractionIssue, ...] = ()

    def mention(self, mention_id: str) -> ExtractedMention | None:
        return next((item for item in self.mentions if item.id == mention_id), None)


class ContributionExtractor(Protocol):
    def extract(self, contribution: UserContribution) -> ContributionExtraction: ...


class ContributionExtractionError(ValueError):
    pass


class _ModelMention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: MentionKind
    source_text: NonBlankText


class _ModelExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mentions: tuple[_ModelMention, ...] = ()


class LlmContributionExtractor:
    """Extract untrusted linguistic mentions without wallet or dialogue context."""

    def __init__(self, *, model: StructuredChatModel) -> None:
        self._model = model

    def extract(self, contribution: UserContribution) -> ContributionExtraction:
        output_schema = _ModelExtraction.model_json_schema()
        retry_feedback: str | None = None
        for attempt in range(2):
            content = self._model.complete(
                system_prompt=_system_prompt(
                    output_schema=output_schema,
                    retry_feedback=retry_feedback,
                ),
                user_prompt=contribution.content,
                output_schema=output_schema,
            )
            try:
                extracted = _ModelExtraction.model_validate_json(content)
            except ValidationError as exc:
                if attempt == 0:
                    retry_feedback = _retry_feedback(content, str(exc))
                    continue
                raise ContributionExtractionError(
                    f"structured model returned an invalid extraction: {content[:300]!r}"
                ) from exc

            result = _anchor_mentions(extracted.mentions, contribution=contribution.content)
            if result.issues and attempt == 0:
                retry_feedback = _retry_feedback(
                    content,
                    "; ".join(issue.reason for issue in result.issues),
                )
                continue
            return result
        raise AssertionError("extraction retry loop did not return")


def _system_prompt(
    *,
    output_schema: dict[str, Any],
    retry_feedback: str | None,
) -> str:
    retry = "" if retry_feedback is None else f"\nRETRY_FEEDBACK={retry_feedback}"
    return (
        "Extract only source-grounded linguistic mentions from the latest user text. "
        "Return one JSON object matching the supplied schema and no Markdown. Preserve "
        "each mention as an exact, case-sensitive substring and return mentions in source "
        "order. Repeat the same text only when it occurs more than once. Use action for "
        "transaction-like verbs, money for complete monetary expressions, date_time for "
        "complete temporal expressions, reference for named or referring entities, "
        "free_text for user-supplied descriptive text, and change for correction, negation, "
        "or clearing cues. Do not assign wallet fields, transaction types, account/category "
        "roles, normalized values, or identifiers. Omit text that cannot support a wallet "
        "transaction update. Extract every potentially relevant named or referring noun "
        "phrase independently, including names such as Payroll, Groceries, Daily checking, "
        "Pocket wallet, or USD cash; do not omit one merely because another reference occurs. "
        "Currency words belong to a money mention only when they are part of a numeric monetary "
        "expression."
        f"\nOUTPUT_SCHEMA={json.dumps(output_schema, separators=(',', ':'), sort_keys=True)}"
        f"{retry}"
    )


def _retry_feedback(content: str, reason: str) -> str:
    return json.dumps(
        {
            "reason": reason[:1000],
            "previous_output": content[:2000],
            "instruction": "Return a corrected object only.",
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def _anchor_mentions(
    mentions: tuple[_ModelMention, ...],
    *,
    contribution: str,
) -> ContributionExtraction:
    anchored: list[tuple[MentionKind, SourceEvidence]] = []
    issues: list[ExtractionIssue] = []
    next_start_by_text: dict[str, int] = {}
    for mention in mentions:
        next_start = next_start_by_text.get(mention.source_text, 0)
        start = contribution.find(mention.source_text, next_start)
        if start < 0:
            issues.append(
                ExtractionIssue(
                    kind=mention.kind,
                    source_text=mention.source_text,
                    reason="source text does not identify another exact contribution span",
                )
            )
            continue
        end = start + len(mention.source_text)
        next_start_by_text[mention.source_text] = end
        evidence = SourceEvidence(start=start, end=end, text=contribution[start:end])
        if (mention.kind, evidence) not in anchored:
            anchored.append((mention.kind, evidence))

    anchored.sort(key=lambda item: (item[1].start, item[1].end, item[0].value))
    extracted = tuple(
        ExtractedMention(id=f"m{index}", kind=kind, evidence=evidence)
        for index, (kind, evidence) in enumerate(anchored)
    )
    return ContributionExtraction(mentions=extracted, issues=tuple(issues))
