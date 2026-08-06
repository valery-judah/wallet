from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Annotated, Any, Protocol

from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

from wallet.ai.llm import StructuredChatModel
from wallet.ai.transaction_capture.domain import (
    CandidateField,
    PendingInteractionKind,
    UserContribution,
    candidate_field_is_relevant,
)
from wallet.ai.transaction_capture.extraction import ContributionExtraction, MentionKind
from wallet.domain.transactions import TransactionType

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class InterpretationOrigin(StrEnum):
    EXPLICIT = "explicit"
    CONTEXTUAL = "contextual"
    INFERRED = "inferred"
    DEFAULTED = "defaulted"


@dataclass(frozen=True, slots=True)
class FieldHypothesis:
    field: CandidateField
    mention_id: str
    origin: InterpretationOrigin
    semantic_value: TransactionType | None = None


@dataclass(frozen=True, slots=True)
class FieldClear:
    field: CandidateField
    mention_id: str
    origin: InterpretationOrigin


@dataclass(frozen=True, slots=True)
class SemanticIssue:
    reason: str
    field: CandidateField | None = None
    mention_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SemanticInterpretation:
    hypotheses: tuple[FieldHypothesis, ...] = ()
    clears: tuple[FieldClear, ...] = ()
    issues: tuple[SemanticIssue, ...] = ()


class SemanticReferenceState(StrEnum):
    UNSET = "unset"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class SemanticReferenceValue:
    state: SemanticReferenceState
    label: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", SemanticReferenceState(self.state))
        if self.state is SemanticReferenceState.AVAILABLE:
            if self.label is None or not self.label.strip():
                raise ValueError("available semantic reference requires a label")
        elif self.label is not None:
            raise ValueError("unset or unavailable semantic reference cannot expose a label")


@dataclass(frozen=True, slots=True)
class SemanticReferenceVocabulary:
    account_labels: tuple[str, ...]
    spending_category_labels: tuple[str, ...]
    income_category_labels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SemanticCandidateContext:
    type: TransactionType | None
    amount_minor: int | None
    occurred_on: date | None
    account: SemanticReferenceValue
    spending_category: SemanticReferenceValue
    income_category: SemanticReferenceValue
    source_account: SemanticReferenceValue
    destination_account: SemanticReferenceValue
    balance_change_minor: int | None
    description: str | None
    merchant_name: str | None
    notes: str | None


@dataclass(frozen=True, slots=True)
class SemanticPendingInteraction:
    kind: PendingInteractionKind
    field: CandidateField | None
    option_labels: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SemanticContext:
    today: date
    candidate: SemanticCandidateContext
    pending_interaction: SemanticPendingInteraction | None
    references: SemanticReferenceVocabulary


class ContributionSemanticInterpreter(Protocol):
    def interpret(
        self,
        contribution: UserContribution,
        *,
        extraction: ContributionExtraction,
        context: SemanticContext,
    ) -> SemanticInterpretation: ...


class SemanticInterpretationError(ValueError):
    pass


class _ModelFieldHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: CandidateField
    mention_id: NonBlankText
    origin: InterpretationOrigin
    semantic_value: str | None = None


class _ModelFieldClear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: CandidateField
    mention_id: NonBlankText
    origin: InterpretationOrigin


class _ModelSemanticInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypotheses: tuple[_ModelFieldHypothesis, ...] = ()
    clears: tuple[_ModelFieldClear, ...] = ()


class LlmContributionSemanticInterpreter:
    """Assign wallet semantics to verified extracted mentions."""

    def __init__(self, *, model: StructuredChatModel) -> None:
        self._model = model

    def interpret(
        self,
        contribution: UserContribution,
        *,
        extraction: ContributionExtraction,
        context: SemanticContext,
    ) -> SemanticInterpretation:
        output_schema = _ModelSemanticInterpretation.model_json_schema()
        retry_feedback: str | None = None
        for attempt in range(2):
            content = self._model.complete(
                system_prompt=_system_prompt(
                    extraction=extraction,
                    context=context,
                    output_schema=output_schema,
                    retry_feedback=retry_feedback,
                ),
                user_prompt=contribution.content,
                output_schema=output_schema,
            )
            try:
                interpreted = _ModelSemanticInterpretation.model_validate_json(content)
            except ValidationError as exc:
                if attempt == 0:
                    retry_feedback = _retry_feedback(content, str(exc))
                    continue
                raise SemanticInterpretationError(
                    f"structured model returned an invalid semantic interpretation: "
                    f"{content[:300]!r}"
                ) from exc

            result = _validate_interpretation(
                interpreted,
                extraction=extraction,
                candidate_type=context.candidate.type,
            )
            if result.issues and attempt == 0:
                retry_feedback = _retry_feedback(
                    content,
                    "; ".join(issue.reason for issue in result.issues),
                )
                continue
            return result
        raise AssertionError("semantic retry loop did not return")


def _system_prompt(
    *,
    extraction: ContributionExtraction,
    context: SemanticContext,
    output_schema: dict[str, Any],
    retry_feedback: str | None,
) -> str:
    prompt_context = {
        "today": context.today.isoformat(),
        "candidate": _candidate_context(context.candidate),
        "pending_interaction": _pending_context(context.pending_interaction),
        "mentions": [
            {
                "id": mention.id,
                "kind": mention.kind.value,
                "text": mention.evidence.text,
                "start": mention.evidence.start,
                "end": mention.evidence.end,
            }
            for mention in extraction.mentions
        ],
        "allowed_hypothesis_fields": _allowed_hypothesis_fields(extraction),
        "available_account_labels": list(context.references.account_labels),
        "available_spending_category_labels": list(context.references.spending_category_labels),
        "available_income_category_labels": list(context.references.income_category_labels),
    }
    retry = "" if retry_feedback is None else f"\nRETRY_FEEDBACK={retry_feedback}"
    return (
        "Interpret the latest wallet contribution using only the supplied verified mention "
        "IDs as evidence. Return one JSON object matching the supplied schema and no "
        "Markdown. Each set or clear must cite exactly one supplied mention_id. Never emit "
        "source text, wallet IDs, or catalog selections. For type, semantic_value must be "
        "expense, income, transfer, or adjustment. For every other field semantic_value must "
        "be null because deterministic grounding uses the cited mention text. For expense, "
        "income, and adjustment use account_id; source_account_id and destination_account_id "
        "are only for transfers. Adjustments use balance_change_minor; other monetary "
        "transactions use amount_minor. Increasing, reducing, or correcting an existing "
        "account balance is always an adjustment, never income or expense. For example, in "
        "'Increase USD cash by 50 dollars today', Increase means adjustment, USD cash is "
        "account_id, and 50 dollars is balance_change_minor. Account and category labels are "
        "read-only vocabulary for recognizing roles. For a transfer such as 'Transfer 100 "
        "pesos from Daily checking "
        "to Pocket wallet', Daily checking is source_account_id and Pocket wallet is "
        "destination_account_id. "
        "Use explicit for directly stated values, contextual for short "
        "answers interpreted through a pending interaction, inferred for meaning implied by "
        "wording, and defaulted only when the user explicitly requests a default. Use clears "
        "only when a change mention explicitly requests removal. Never emit occurred_on unless "
        "it cites a date_time mention, and never emit a monetary field unless it cites a money "
        "mention. A hypothesis field MUST appear in CONTEXT.allowed_hypothesis_fields. Existing "
        "candidate values are context, not output, unless changed or cleared."
        f"\nCONTEXT={json.dumps(prompt_context, separators=(',', ':'), sort_keys=True)}"
        f"\nOUTPUT_SCHEMA={json.dumps(output_schema, separators=(',', ':'), sort_keys=True)}"
        f"{retry}"
    )


def _validate_interpretation(
    interpreted: _ModelSemanticInterpretation,
    *,
    extraction: ContributionExtraction,
    candidate_type: TransactionType | None,
) -> SemanticInterpretation:
    mention_by_id = {mention.id: mention for mention in extraction.mentions}
    hypotheses: list[FieldHypothesis] = []
    clears: list[FieldClear] = []
    issues: list[SemanticIssue] = []

    for item in interpreted.hypotheses:
        mention = mention_by_id.get(item.mention_id)
        if mention is None:
            issues.append(
                SemanticIssue(
                    field=item.field,
                    mention_ids=(item.mention_id,),
                    reason="semantic hypothesis cites an unknown mention",
                )
            )
            continue
        expected_kind = _required_mention_kind(item.field)
        if expected_kind is not None and mention.kind is not expected_kind:
            issues.append(
                SemanticIssue(
                    field=item.field,
                    mention_ids=(item.mention_id,),
                    reason=(f"{item.field.value} requires a {expected_kind.value} mention"),
                )
            )
            continue
        if item.field is CandidateField.TYPE:
            if item.semantic_value is None:
                issues.append(
                    SemanticIssue(
                        field=item.field,
                        mention_ids=(item.mention_id,),
                        reason="transaction type requires a supported semantic value",
                    )
                )
                continue
            try:
                semantic_value = TransactionType(item.semantic_value)
            except ValueError:
                issues.append(
                    SemanticIssue(
                        field=item.field,
                        mention_ids=(item.mention_id,),
                        reason="transaction type requires a supported semantic value",
                    )
                )
                continue
        else:
            semantic_value = None
        hypotheses.append(
            FieldHypothesis(
                field=item.field,
                mention_id=item.mention_id,
                origin=item.origin,
                semantic_value=semantic_value,
            )
        )

    for clear_item in interpreted.clears:
        mention = mention_by_id.get(clear_item.mention_id)
        if mention is None:
            issues.append(
                SemanticIssue(
                    field=clear_item.field,
                    mention_ids=(clear_item.mention_id,),
                    reason="semantic clear cites an unknown mention",
                )
            )
            continue
        if mention.kind is not MentionKind.CHANGE:
            issues.append(
                SemanticIssue(
                    field=clear_item.field,
                    mention_ids=(clear_item.mention_id,),
                    reason="clear operation requires a change or removal mention",
                )
            )
            continue
        clears.append(
            FieldClear(
                field=clear_item.field,
                mention_id=clear_item.mention_id,
                origin=clear_item.origin,
            )
        )

    hypotheses, clears, conflict_issues = _remove_conflicting_fields(hypotheses, clears)
    issues.extend(conflict_issues)
    effective_type = _effective_type(hypotheses, candidate_type=candidate_type)
    retained_hypotheses: list[FieldHypothesis] = []
    for hypothesis in hypotheses:
        if hypothesis.field is CandidateField.TYPE or _field_is_relevant(
            hypothesis.field, transaction_type=effective_type
        ):
            retained_hypotheses.append(hypothesis)
        else:
            issues.append(
                SemanticIssue(
                    field=hypothesis.field,
                    mention_ids=(hypothesis.mention_id,),
                    reason="field is incompatible with the interpreted transaction type",
                )
            )
    retained_clears: list[FieldClear] = []
    for clear in clears:
        if clear.field is CandidateField.TYPE or _field_is_relevant(
            clear.field, transaction_type=effective_type
        ):
            retained_clears.append(clear)
        else:
            issues.append(
                SemanticIssue(
                    field=clear.field,
                    mention_ids=(clear.mention_id,),
                    reason="cleared field is incompatible with the transaction type",
                )
            )
    return SemanticInterpretation(
        hypotheses=tuple(retained_hypotheses),
        clears=tuple(retained_clears),
        issues=tuple(issues),
    )


def _remove_conflicting_fields(
    hypotheses: list[FieldHypothesis],
    clears: list[FieldClear],
) -> tuple[list[FieldHypothesis], list[FieldClear], list[SemanticIssue]]:
    claims: dict[CandidateField, list[str]] = {}
    combined: list[FieldHypothesis | FieldClear] = [*hypotheses, *clears]
    for item in combined:
        claims.setdefault(item.field, []).append(item.mention_id)
    conflicts = {field: ids for field, ids in claims.items() if len(ids) > 1}
    issues = [
        SemanticIssue(
            field=field,
            mention_ids=tuple(ids),
            reason="semantic output contains conflicting operations for one field",
        )
        for field, ids in conflicts.items()
    ]
    return (
        [item for item in hypotheses if item.field not in conflicts],
        [item for item in clears if item.field not in conflicts],
        issues,
    )


def _effective_type(
    hypotheses: list[FieldHypothesis],
    *,
    candidate_type: TransactionType | None,
) -> TransactionType | None:
    return next(
        (
            item.semantic_value
            for item in hypotheses
            if item.field is CandidateField.TYPE and item.semantic_value is not None
        ),
        candidate_type,
    )


def _field_is_relevant(
    field: CandidateField,
    *,
    transaction_type: TransactionType | None,
) -> bool:
    if transaction_type is None:
        return True
    return candidate_field_is_relevant(field, transaction_type=transaction_type)


def _candidate_context(candidate: SemanticCandidateContext) -> dict[str, Any]:
    return {
        "type": _json_value(candidate.type),
        "amount_minor": candidate.amount_minor,
        "occurred_on": _json_value(candidate.occurred_on),
        "account_id": _reference_context(candidate.account),
        "spending_category_id": _reference_context(candidate.spending_category),
        "income_category_id": _reference_context(candidate.income_category),
        "source_account_id": _reference_context(candidate.source_account),
        "destination_account_id": _reference_context(candidate.destination_account),
        "balance_change_minor": candidate.balance_change_minor,
        "description": candidate.description,
        "merchant_name": candidate.merchant_name,
        "notes": candidate.notes,
    }


def _required_mention_kind(field: CandidateField) -> MentionKind | None:
    if field in {CandidateField.AMOUNT_MINOR, CandidateField.BALANCE_CHANGE_MINOR}:
        return MentionKind.MONEY
    if field is CandidateField.OCCURRED_ON:
        return MentionKind.DATE_TIME
    return None


def _allowed_hypothesis_fields(extraction: ContributionExtraction) -> list[str]:
    kinds = {mention.kind for mention in extraction.mentions}
    excluded: set[CandidateField] = set()
    if MentionKind.MONEY not in kinds:
        excluded.update({CandidateField.AMOUNT_MINOR, CandidateField.BALANCE_CHANGE_MINOR})
    if MentionKind.DATE_TIME not in kinds:
        excluded.add(CandidateField.OCCURRED_ON)
    return [field.value for field in CandidateField if field not in excluded]


def _pending_context(pending: SemanticPendingInteraction | None) -> dict[str, Any] | None:
    if pending is None:
        return None
    return {
        "kind": pending.kind.value,
        "field": pending.field.value if pending.field is not None else None,
        "options": list(pending.option_labels),
    }


def _reference_context(reference: SemanticReferenceValue) -> dict[str, str | None]:
    return {"state": reference.state.value, "label": reference.label}


def _json_value(value: object) -> object:
    if isinstance(value, (date, TransactionType)):
        return value.isoformat() if isinstance(value, date) else value.value
    return value


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
