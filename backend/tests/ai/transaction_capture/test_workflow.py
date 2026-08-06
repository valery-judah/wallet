from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from threading import Event

import pytest

from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CandidatePatch,
    CaptureStatus,
    InteractionOption,
    InvalidCaptureTransitionError,
    PendingInteraction,
    PendingInteractionKind,
    TransactionCandidate,
    UserContribution,
)
from wallet.ai.transaction_capture.extraction import (
    ContributionExtraction,
    ExtractionIssue,
    MentionKind,
    SourceEvidence,
)
from wallet.ai.transaction_capture.grounding import (
    GroundedInterpretation,
    GroundingAmbiguity,
    GroundingOption,
    UnresolvedField,
)
from wallet.ai.transaction_capture.processing import (
    CandidateReduction,
    ContributionAnalysisPath,
    ContributionProcessingResult,
    ContributionProcessingTrace,
)
from wallet.ai.transaction_capture.semantic import SemanticInterpretation, SemanticIssue
from wallet.ai.transaction_capture.workflow import (
    CaptureOutcome,
    CaptureResult,
    CaptureSessionNotFoundError,
    CaptureWorkflow,
)
from wallet.domain.transactions import TransactionType

TODAY = date(2026, 8, 4)


@dataclass(frozen=True)
class InterpreterCall:
    candidate: TransactionCandidate
    pending_interaction: PendingInteraction | None
    on_date: date = TODAY


@dataclass
class StubProcessor:
    interpretations: dict[str, CandidatePatch]
    calls: list[InterpreterCall] = field(default_factory=list)
    failures: dict[str, Exception] = field(default_factory=dict)

    def process(
        self,
        contribution: UserContribution,
        *,
        candidate: TransactionCandidate,
        pending_interaction: PendingInteraction | None,
        on_date: date,
    ) -> ContributionProcessingResult:
        failure = self.failures.get(contribution.content)
        if failure is not None:
            raise failure
        self.calls.append(
            InterpreterCall(
                candidate=candidate,
                pending_interaction=pending_interaction,
                on_date=on_date,
            )
        )
        patch = self.interpretations[contribution.content]
        next_candidate = candidate.apply(patch)
        reduction = CandidateReduction(patch=patch, candidate=next_candidate)
        return ContributionProcessingResult(
            candidate=next_candidate,
            trace=ContributionProcessingTrace(
                analysis_path=ContributionAnalysisPath.MODEL_PIPELINE,
                extraction=ContributionExtraction(),
                semantic_interpretation=SemanticInterpretation(),
                grounded_interpretation=GroundedInterpretation(patch=patch),
                candidate_reduction=reduction,
            ),
        )


@dataclass
class BlockingProcessor:
    delegate: StubProcessor
    blocked_content: str
    entered: Event = field(default_factory=Event)
    release: Event = field(default_factory=Event)

    def process(
        self,
        contribution: UserContribution,
        *,
        candidate: TransactionCandidate,
        pending_interaction: PendingInteraction | None,
        on_date: date,
    ) -> ContributionProcessingResult:
        if contribution.content == self.blocked_content:
            self.entered.set()
            if not self.release.wait(timeout=2):
                raise TimeoutError("test did not release blocked capture processing")
        return self.delegate.process(
            contribution,
            candidate=candidate,
            pending_interaction=pending_interaction,
            on_date=on_date,
        )


@dataclass
class FixedProcessor:
    result: ContributionProcessingResult

    def process(
        self,
        contribution: UserContribution,
        *,
        candidate: TransactionCandidate,
        pending_interaction: PendingInteraction | None,
        on_date: date,
    ) -> ContributionProcessingResult:
        return self.result


def interpretation_patch(*, patch: CandidatePatch | None = None) -> CandidatePatch:
    """Keep existing workflow fixtures concise while stubbing the processor."""

    return patch or CandidatePatch()


@dataclass
class StubValidator:
    rejected_fields: list[CandidateField | None] = field(default_factory=list)
    calls: list[TransactionCandidate] = field(default_factory=list)

    def invalid_field(self, candidate: TransactionCandidate) -> CandidateField | None:
        self.calls.append(candidate)
        if not self.rejected_fields:
            return None
        return self.rejected_fields.pop(0)


@dataclass
class StubWallet:
    transaction_id: str = "transaction_1"
    failures: list[Exception] = field(default_factory=list)
    calls: list[TransactionCandidate] = field(default_factory=list)

    def execute(self, candidate: TransactionCandidate) -> str:
        self.calls.append(candidate)
        if self.failures:
            raise self.failures.pop(0)
        return self.transaction_id


def _complete_expense_patch() -> CandidatePatch:
    return CandidatePatch(
        type=TransactionType.EXPENSE,
        amount_minor=4000,
        account_id="cash",
        spending_category_id="dining",
    )


def test_transaction_candidate_is_built_progressively_across_contributions() -> None:
    workflow, interpreter, validator, wallet = _workflow(
        {
            "Record an expense": interpretation_patch(
                patch=CandidatePatch(type=TransactionType.EXPENSE)
            ),
            "$40": interpretation_patch(patch=CandidatePatch(amount_minor=4000)),
            "Cash": interpretation_patch(patch=CandidatePatch(account_id="cash")),
            "Dining": interpretation_patch(patch=CandidatePatch(spending_category_id="dining")),
        }
    )

    type_result = workflow.receive(UserContribution("Record an expense"))
    capture_id = type_result.session.id
    amount_result = workflow.receive(UserContribution("$40"), capture_id=capture_id)
    account_result = workflow.receive(UserContribution("Cash"), capture_id=capture_id)
    ready = workflow.receive(UserContribution("Dining"), capture_id=capture_id)

    candidates = [
        TransactionCandidate(type=TransactionType.EXPENSE, occurred_on=TODAY),
        TransactionCandidate(
            type=TransactionType.EXPENSE,
            amount_minor=4000,
            occurred_on=TODAY,
        ),
        TransactionCandidate(
            type=TransactionType.EXPENSE,
            amount_minor=4000,
            occurred_on=TODAY,
            account_id="cash",
        ),
        TransactionCandidate(
            type=TransactionType.EXPENSE,
            amount_minor=4000,
            occurred_on=TODAY,
            account_id="cash",
            spending_category_id="dining",
        ),
    ]
    interactions = [
        PendingInteraction(
            kind=PendingInteractionKind.REQUEST_VALUE,
            field=CandidateField.AMOUNT_MINOR,
        ),
        PendingInteraction(
            kind=PendingInteractionKind.REQUEST_VALUE,
            field=CandidateField.ACCOUNT_ID,
        ),
        PendingInteraction(
            kind=PendingInteractionKind.REQUEST_VALUE,
            field=CandidateField.SPENDING_CATEGORY_ID,
        ),
        None,
    ]
    results = [type_result, amount_result, account_result, ready]

    assert [result.session.id for result in results] == [capture_id] * 4
    assert [result.session.candidate for result in results] == candidates
    assert [result.session.pending_interaction for result in results] == interactions
    assert [result.outcome for result in results] == [
        CaptureOutcome.AWAITING_INTERACTION,
        CaptureOutcome.AWAITING_INTERACTION,
        CaptureOutcome.AWAITING_INTERACTION,
        CaptureOutcome.AWAITING_CONFIRMATION,
    ]
    assert ready.session.status is CaptureStatus.AWAITING_CONFIRMATION
    assert ready.session.transaction_id is None

    assert interpreter.calls == [
        InterpreterCall(
            candidate=TransactionCandidate(occurred_on=TODAY),
            pending_interaction=None,
        ),
        InterpreterCall(candidate=candidates[0], pending_interaction=interactions[0]),
        InterpreterCall(candidate=candidates[1], pending_interaction=interactions[1]),
        InterpreterCall(candidate=candidates[2], pending_interaction=interactions[2]),
    ]
    assert validator.calls == [candidates[-1]]
    assert wallet.calls == []

    completed = workflow.confirm(capture_id)

    assert completed.outcome is CaptureOutcome.COMPLETED
    assert completed.session.transaction_id == "transaction_1"
    assert validator.calls == [candidates[-1], candidates[-1]]
    assert wallet.calls == [candidates[-1]]


def test_missing_transaction_type_is_requested_before_validation() -> None:
    workflow, _, validator, wallet = _workflow({"Record something": interpretation_patch()})

    result = workflow.receive(UserContribution("Record something"))

    assert result.outcome is CaptureOutcome.AWAITING_INTERACTION
    assert result.session.candidate == TransactionCandidate(occurred_on=TODAY)
    assert result.session.pending_interaction == PendingInteraction(
        kind=PendingInteractionKind.REQUEST_VALUE,
        field=CandidateField.TYPE,
    )
    assert validator.calls == []
    assert wallet.calls == []


def test_workflow_samples_date_once_and_shares_it_with_session_and_processor() -> None:
    date_calls = 0

    def today() -> date:
        nonlocal date_calls
        date_calls += 1
        return TODAY

    processor = StubProcessor({"Record something": CandidatePatch()})
    workflow = CaptureWorkflow(
        processor=processor,
        validator=StubValidator(),
        wallet=StubWallet(),
        today=today,
        generate_capture_id=lambda: "capture_date",
    )

    result = workflow.receive(UserContribution("Record something"))

    assert date_calls == 1
    assert result.session.candidate.occurred_on == TODAY
    assert processor.calls[0].on_date == TODAY


@pytest.mark.parametrize(
    ("patch", "expected_candidate"),
    [
        (
            CandidatePatch(
                type=TransactionType.EXPENSE,
                amount_minor=4000,
                account_id="cash",
                spending_category_id="dining",
            ),
            TransactionCandidate(
                type=TransactionType.EXPENSE,
                amount_minor=4000,
                occurred_on=TODAY,
                account_id="cash",
                spending_category_id="dining",
            ),
        ),
        (
            CandidatePatch(
                type=TransactionType.INCOME,
                amount_minor=250000,
                account_id="checking",
                income_category_id="salary",
            ),
            TransactionCandidate(
                type=TransactionType.INCOME,
                amount_minor=250000,
                occurred_on=TODAY,
                account_id="checking",
                income_category_id="salary",
            ),
        ),
        (
            CandidatePatch(
                type=TransactionType.TRANSFER,
                amount_minor=50000,
                source_account_id="checking",
                destination_account_id="savings",
            ),
            TransactionCandidate(
                type=TransactionType.TRANSFER,
                amount_minor=50000,
                occurred_on=TODAY,
                source_account_id="checking",
                destination_account_id="savings",
            ),
        ),
        (
            CandidatePatch(
                type=TransactionType.ADJUSTMENT,
                account_id="cash",
                balance_change_minor=5000,
            ),
            TransactionCandidate(
                type=TransactionType.ADJUSTMENT,
                occurred_on=TODAY,
                account_id="cash",
                balance_change_minor=5000,
            ),
        ),
        (
            CandidatePatch(
                type=TransactionType.ADJUSTMENT,
                account_id="cash",
                balance_change_minor=-2000,
            ),
            TransactionCandidate(
                type=TransactionType.ADJUSTMENT,
                occurred_on=TODAY,
                account_id="cash",
                balance_change_minor=-2000,
            ),
        ),
    ],
    ids=("expense", "income", "transfer", "positive-adjustment", "negative-adjustment"),
)
def test_complete_supported_candidate_previews_then_executes_once(
    patch: CandidatePatch,
    expected_candidate: TransactionCandidate,
) -> None:
    workflow, _, validator, wallet = _workflow({"Complete": interpretation_patch(patch=patch)})

    ready = workflow.receive(UserContribution("Complete"))

    assert ready.outcome is CaptureOutcome.AWAITING_CONFIRMATION
    assert ready.session.candidate == expected_candidate
    assert ready.session.transaction_id is None
    assert validator.calls == [expected_candidate]
    assert wallet.calls == []

    completed = workflow.confirm(ready.session.id)

    assert completed.outcome is CaptureOutcome.COMPLETED
    assert completed.session.transaction_id == "transaction_1"
    assert validator.calls == [expected_candidate, expected_candidate]
    assert wallet.calls == [expected_candidate]


def test_follow_up_applies_every_interpreted_field_before_progressing() -> None:
    workflow, interpreter, validator, wallet = _workflow(
        {
            "Record an expense": interpretation_patch(
                patch=CandidatePatch(type=TransactionType.EXPENSE)
            ),
            "$35 from Cash for Groceries": interpretation_patch(
                patch=CandidatePatch(
                    amount_minor=3500,
                    account_id="cash",
                    spending_category_id="groceries",
                )
            ),
        }
    )
    first = workflow.receive(UserContribution("Record an expense"))

    ready = workflow.receive(
        UserContribution("$35 from Cash for Groceries"),
        capture_id=first.session.id,
    )

    expected = TransactionCandidate(
        type=TransactionType.EXPENSE,
        amount_minor=3500,
        occurred_on=TODAY,
        account_id="cash",
        spending_category_id="groceries",
    )
    assert interpreter.calls[1].pending_interaction == PendingInteraction(
        kind=PendingInteractionKind.REQUEST_VALUE,
        field=CandidateField.AMOUNT_MINOR,
    )
    assert ready.outcome is CaptureOutcome.AWAITING_CONFIRMATION
    assert ready.session.candidate == expected
    assert validator.calls == [expected]
    assert wallet.calls == []

    completed = workflow.confirm(ready.session.id)
    assert completed.outcome is CaptureOutcome.COMPLETED
    assert wallet.calls == [expected]


def test_explicit_date_and_optional_metadata_reach_wallet_unchanged() -> None:
    occurred_on = date(2026, 8, 1)
    workflow, _, _, wallet = _workflow(
        {
            "Complete with details": interpretation_patch(
                patch=CandidatePatch(
                    type=TransactionType.EXPENSE,
                    amount_minor=2500,
                    occurred_on=occurred_on,
                    account_id="cash",
                    spending_category_id="dining",
                    description="Team lunch",
                    merchant_name="Corner Cafe",
                    notes="Reimbursable",
                )
            )
        }
    )

    result = workflow.receive(UserContribution("Complete with details"))

    assert result.session.candidate == TransactionCandidate(
        type=TransactionType.EXPENSE,
        amount_minor=2500,
        occurred_on=occurred_on,
        account_id="cash",
        spending_category_id="dining",
        description="Team lunch",
        merchant_name="Corner Cafe",
        notes="Reimbursable",
    )
    assert result.outcome is CaptureOutcome.AWAITING_CONFIRMATION
    assert wallet.calls == []

    workflow.confirm(result.session.id)
    assert wallet.calls == [result.session.candidate]


@pytest.mark.parametrize(
    ("patch", "invalid_field"),
    [
        (
            CandidatePatch(
                type=TransactionType.EXPENSE,
                amount_minor=0,
                account_id="cash",
                spending_category_id="dining",
            ),
            CandidateField.AMOUNT_MINOR,
        ),
        (
            CandidatePatch(
                type=TransactionType.INCOME,
                amount_minor=0,
                account_id="checking",
                income_category_id="salary",
            ),
            CandidateField.AMOUNT_MINOR,
        ),
        (
            CandidatePatch(
                type=TransactionType.TRANSFER,
                amount_minor=0,
                source_account_id="checking",
                destination_account_id="savings",
            ),
            CandidateField.AMOUNT_MINOR,
        ),
        (
            CandidatePatch(
                type=TransactionType.ADJUSTMENT,
                account_id="cash",
                balance_change_minor=0,
            ),
            CandidateField.BALANCE_CHANGE_MINOR,
        ),
        (
            CandidatePatch(
                type=TransactionType.TRANSFER,
                amount_minor=10000,
                source_account_id="checking",
                destination_account_id="checking",
            ),
            CandidateField.DESTINATION_ACCOUNT_ID,
        ),
    ],
    ids=("expense", "income", "transfer", "adjustment", "same-account-transfer"),
)
def test_locally_invalid_field_is_cleared_before_context_validation(
    patch: CandidatePatch,
    invalid_field: CandidateField,
) -> None:
    workflow, _, validator, wallet = _workflow({"Invalid": interpretation_patch(patch=patch)})

    result = workflow.receive(UserContribution("Invalid"))

    assert result.outcome is CaptureOutcome.AWAITING_INTERACTION
    assert getattr(result.session.candidate, invalid_field.value) is None
    assert result.session.pending_interaction == PendingInteraction(
        kind=PendingInteractionKind.CORRECT,
        field=invalid_field,
    )
    assert validator.calls == []
    assert wallet.calls == []


@pytest.mark.parametrize(
    ("patch", "invalid_field"),
    [
        (_complete_expense_patch(), CandidateField.ACCOUNT_ID),
        (_complete_expense_patch(), CandidateField.SPENDING_CATEGORY_ID),
        (
            CandidatePatch(
                type=TransactionType.INCOME,
                amount_minor=250000,
                account_id="checking",
                income_category_id="salary",
            ),
            CandidateField.INCOME_CATEGORY_ID,
        ),
        (
            CandidatePatch(
                type=TransactionType.TRANSFER,
                amount_minor=50000,
                source_account_id="checking",
                destination_account_id="savings",
            ),
            CandidateField.SOURCE_ACCOUNT_ID,
        ),
        (
            CandidatePatch(
                type=TransactionType.TRANSFER,
                amount_minor=50000,
                source_account_id="checking",
                destination_account_id="savings",
            ),
            CandidateField.DESTINATION_ACCOUNT_ID,
        ),
        (_complete_expense_patch(), CandidateField.OCCURRED_ON),
    ],
    ids=(
        "account",
        "spending-category",
        "income-category",
        "transfer-source",
        "transfer-destination",
        "date",
    ),
)
def test_contextually_invalid_field_is_cleared_and_requested(
    patch: CandidatePatch,
    invalid_field: CandidateField,
) -> None:
    workflow, _, validator, wallet = _workflow(
        {"Complete": interpretation_patch(patch=patch)},
        rejected_fields=[invalid_field],
    )

    result = workflow.receive(UserContribution("Complete"))

    assert len(validator.calls) == 1
    assert getattr(validator.calls[0], invalid_field.value) is not None
    assert getattr(result.session.candidate, invalid_field.value) is None
    assert result.session.pending_interaction == PendingInteraction(
        kind=PendingInteractionKind.CORRECT,
        field=invalid_field,
    )
    assert wallet.calls == []


def test_corrected_field_is_revalidated_before_execution() -> None:
    workflow, _, validator, wallet = _workflow(
        {
            "Complete": interpretation_patch(patch=_complete_expense_patch()),
            "Checking": interpretation_patch(patch=CandidatePatch(account_id="checking")),
        },
        rejected_fields=[CandidateField.ACCOUNT_ID, None],
    )
    rejected = workflow.receive(UserContribution("Complete"))

    ready = workflow.receive(
        UserContribution("Checking"),
        capture_id=rejected.session.id,
    )

    assert rejected.session.candidate.account_id is None
    assert rejected.session.pending_interaction == PendingInteraction(
        kind=PendingInteractionKind.CORRECT,
        field=CandidateField.ACCOUNT_ID,
    )
    assert ready.outcome is CaptureOutcome.AWAITING_CONFIRMATION
    assert ready.session.candidate.account_id == "checking"
    assert len(validator.calls) == 2
    assert wallet.calls == []

    completed = workflow.confirm(ready.session.id)
    assert completed.outcome is CaptureOutcome.COMPLETED
    assert len(validator.calls) == 3
    assert wallet.calls == [completed.session.candidate]


def test_wallet_error_propagates_and_retains_confirmation_candidate() -> None:
    workflow, interpreter, validator, wallet = _workflow(
        {
            "Record an expense": interpretation_patch(
                patch=CandidatePatch(type=TransactionType.EXPENSE)
            ),
            "Complete": interpretation_patch(
                patch=CandidatePatch(
                    amount_minor=4000,
                    account_id="cash",
                    spending_category_id="dining",
                )
            ),
        },
        wallet_failures=[RuntimeError("wallet unavailable")],
    )
    started = workflow.receive(UserContribution("Record an expense"))

    ready = workflow.receive(UserContribution("Complete"), capture_id=started.session.id)

    with pytest.raises(RuntimeError, match="wallet unavailable"):
        workflow.confirm(started.session.id)

    retained = workflow.get(started.session.id)
    completed = workflow.confirm(started.session.id)

    retained_candidate = ready.session.candidate
    assert retained_candidate.is_complete
    assert retained.session == ready.session
    assert retained.outcome is CaptureOutcome.AWAITING_CONFIRMATION
    assert len(interpreter.calls) == 2
    assert validator.calls == [retained_candidate, retained_candidate, retained_candidate]
    assert wallet.calls == [retained_candidate, retained_candidate]
    assert completed.outcome is CaptureOutcome.COMPLETED


def test_completed_capture_rejects_later_contributions() -> None:
    workflow, interpreter, _, wallet = _workflow(
        {"Complete": interpretation_patch(patch=_complete_expense_patch())}
    )
    ready = workflow.receive(UserContribution("Complete"))
    completed = workflow.confirm(ready.session.id)

    with pytest.raises(InvalidCaptureTransitionError, match="status is completed"):
        workflow.receive(
            UserContribution("not interpreted"),
            capture_id=completed.session.id,
        )

    assert len(interpreter.calls) == 1
    assert len(wallet.calls) == 1


def test_awaiting_confirmation_accepts_edits_and_requires_a_fresh_confirmation() -> None:
    workflow, interpreter, validator, wallet = _workflow(
        {
            "Complete": interpretation_patch(patch=_complete_expense_patch()),
            "Make it 35": interpretation_patch(patch=CandidatePatch(amount_minor=3500)),
        }
    )
    first_preview = workflow.receive(UserContribution("Complete"))

    revised_preview = workflow.receive(
        UserContribution("Make it 35"),
        capture_id=first_preview.session.id,
    )

    assert interpreter.calls[-1].candidate == first_preview.session.candidate
    assert revised_preview.outcome is CaptureOutcome.AWAITING_CONFIRMATION
    assert revised_preview.session.candidate.amount_minor == 3500
    assert wallet.calls == []

    completed = workflow.confirm(revised_preview.session.id)
    assert completed.session.candidate.amount_minor == 3500
    assert len(validator.calls) == 3
    assert wallet.calls == [completed.session.candidate]


def test_confirmation_revalidates_stale_references_before_execution() -> None:
    workflow, _, validator, wallet = _workflow(
        {"Complete": interpretation_patch(patch=_complete_expense_patch())},
        rejected_fields=[None, CandidateField.ACCOUNT_ID],
    )
    ready = workflow.receive(UserContribution("Complete"))

    result = workflow.confirm(ready.session.id)

    assert result.outcome is CaptureOutcome.AWAITING_INTERACTION
    assert result.session.candidate.account_id is None
    assert result.session.pending_interaction == PendingInteraction(
        kind=PendingInteractionKind.CORRECT,
        field=CandidateField.ACCOUNT_ID,
    )
    assert len(validator.calls) == 2
    assert wallet.calls == []


def test_cancellation_is_idempotent_and_terminal() -> None:
    workflow, _, _, wallet = _workflow(
        {"Complete": interpretation_patch(patch=_complete_expense_patch())}
    )
    ready = workflow.receive(UserContribution("Complete"))

    cancelled = workflow.cancel(ready.session.id)
    repeated = workflow.cancel(ready.session.id)

    assert cancelled.outcome is CaptureOutcome.CANCELLED
    assert repeated.session == cancelled.session
    assert cancelled.session.candidate == ready.session.candidate
    assert wallet.calls == []
    with pytest.raises(InvalidCaptureTransitionError, match="status is cancelled"):
        workflow.confirm(ready.session.id)
    with pytest.raises(InvalidCaptureTransitionError, match="status is cancelled"):
        workflow.receive(UserContribution("Complete"), capture_id=ready.session.id)


def test_processing_failures_roll_back_existing_and_unreturned_new_sessions() -> None:
    workflow, processor, _, _ = _workflow(
        {"Start": interpretation_patch(patch=CandidatePatch(type=TransactionType.EXPENSE))}
    )
    started = workflow.receive(UserContribution("Start"))
    processor.failures["Broken"] = RuntimeError("model unavailable")

    with pytest.raises(RuntimeError, match="model unavailable"):
        workflow.receive(UserContribution("Broken"), capture_id=started.session.id)
    assert workflow.get(started.session.id).session == started.session

    fresh, fresh_processor, _, _ = _workflow({})
    fresh_processor.failures["Broken"] = RuntimeError("model unavailable")
    with pytest.raises(RuntimeError, match="model unavailable"):
        fresh.receive(UserContribution("Broken"))
    with pytest.raises(CaptureSessionNotFoundError, match="capture_1"):
        fresh.get("capture_1")

    preview, preview_processor, _, _ = _workflow(
        {"Complete": interpretation_patch(patch=_complete_expense_patch())}
    )
    ready = preview.receive(UserContribution("Complete"))
    preview_processor.failures["Broken edit"] = RuntimeError("model unavailable")
    with pytest.raises(RuntimeError, match="model unavailable"):
        preview.receive(UserContribution("Broken edit"), capture_id=ready.session.id)
    assert preview.get(ready.session.id).session == ready.session


def test_new_capture_is_not_published_until_initial_processing_succeeds() -> None:
    processor = BlockingProcessor(
        delegate=StubProcessor(
            {"Start": interpretation_patch(patch=CandidatePatch(type=TransactionType.EXPENSE))}
        ),
        blocked_content="Start",
    )
    workflow = CaptureWorkflow(
        processor=processor,
        validator=StubValidator(),
        wallet=StubWallet(),
        today=lambda: TODAY,
        generate_capture_id=lambda: "capture_1",
    )

    with ThreadPoolExecutor(max_workers=1) as executor:
        receive_future = executor.submit(workflow.receive, UserContribution("Start"))
        assert processor.entered.wait(timeout=2)
        try:
            with pytest.raises(CaptureSessionNotFoundError, match="capture_1"):
                workflow.get("capture_1")
        finally:
            processor.release.set()
        created = receive_future.result(timeout=2)

    assert workflow.get("capture_1").session == created.session


def test_read_waits_for_an_in_flight_update_and_observes_the_committed_session() -> None:
    processor = BlockingProcessor(
        delegate=StubProcessor(
            {
                "Start": interpretation_patch(patch=CandidatePatch(type=TransactionType.EXPENSE)),
                "$40": interpretation_patch(patch=CandidatePatch(amount_minor=4000)),
            }
        ),
        blocked_content="$40",
    )
    workflow = CaptureWorkflow(
        processor=processor,
        validator=StubValidator(),
        wallet=StubWallet(),
        today=lambda: TODAY,
        generate_capture_id=lambda: "capture_1",
    )
    started = workflow.receive(UserContribution("Start"))
    getter_started = Event()

    def read_capture() -> CaptureResult:
        getter_started.set()
        return workflow.get(started.session.id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        update_future = executor.submit(
            workflow.receive,
            UserContribution("$40"),
            capture_id=started.session.id,
        )
        assert processor.entered.wait(timeout=2)
        read_future = executor.submit(read_capture)
        assert getter_started.wait(timeout=2)
        try:
            assert not read_future.done()
        finally:
            processor.release.set()
        updated = update_future.result(timeout=2)
        observed = read_future.result(timeout=2)

    assert observed.session == updated.session
    assert observed.session.candidate.amount_minor == 4000


def test_slow_processing_for_one_capture_does_not_block_another_capture() -> None:
    processor = BlockingProcessor(
        delegate=StubProcessor(
            {
                "Start one": interpretation_patch(
                    patch=CandidatePatch(type=TransactionType.EXPENSE)
                ),
                "Start two": interpretation_patch(
                    patch=CandidatePatch(type=TransactionType.EXPENSE)
                ),
                "Block one": interpretation_patch(patch=CandidatePatch(amount_minor=1000)),
                "Advance two": interpretation_patch(patch=CandidatePatch(amount_minor=2000)),
            }
        ),
        blocked_content="Block one",
    )
    capture_ids = iter(("capture_1", "capture_2"))
    workflow = CaptureWorkflow(
        processor=processor,
        validator=StubValidator(),
        wallet=StubWallet(),
        today=lambda: TODAY,
        generate_capture_id=lambda: next(capture_ids),
    )
    first = workflow.receive(UserContribution("Start one"))
    second = workflow.receive(UserContribution("Start two"))

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(
            workflow.receive,
            UserContribution("Block one"),
            capture_id=first.session.id,
        )
        assert processor.entered.wait(timeout=2)
        second_future = executor.submit(
            workflow.receive,
            UserContribution("Advance two"),
            capture_id=second.session.id,
        )
        try:
            advanced_second = second_future.result(timeout=1)
        finally:
            processor.release.set()
        advanced_first = first_future.result(timeout=2)

    assert advanced_first.session.candidate.amount_minor == 1000
    assert advanced_second.session.candidate.amount_minor == 2000


def test_duplicate_generated_capture_id_does_not_replace_the_published_session() -> None:
    workflow, _, _, _ = _workflow(
        {"Start": interpretation_patch(patch=CandidatePatch(type=TransactionType.EXPENSE))}
    )
    first = workflow.receive(UserContribution("Start"))

    with pytest.raises(ValueError, match="capture session already exists: capture_1"):
        workflow.receive(UserContribution("Start"))

    assert workflow.get(first.session.id).session == first.session


def test_concurrent_confirmation_creates_exactly_one_transaction() -> None:
    workflow, _, validator, wallet = _workflow(
        {"Complete": interpretation_patch(patch=_complete_expense_patch())}
    )
    ready = workflow.receive(UserContribution("Complete"))

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: workflow.confirm(ready.session.id), range(2)))

    assert [result.outcome for result in results] == [
        CaptureOutcome.COMPLETED,
        CaptureOutcome.COMPLETED,
    ]
    assert len(validator.calls) == 2
    assert wallet.calls == [ready.session.candidate]


def test_grounding_ambiguity_blocks_execution_and_exposes_trace() -> None:
    ambiguity = GroundingAmbiguity(
        field=CandidateField.SPENDING_CATEGORY_ID,
        evidence=SourceEvidence(0, 6, "Coffee"),
        options=(
            GroundingOption("food_coffee", "Food > Coffee"),
            GroundingOption("work_coffee", "Work > Coffee"),
        ),
        reason="ambiguous",
    )
    candidate = TransactionCandidate(
        type=TransactionType.EXPENSE,
        amount_minor=3500,
        occurred_on=TODAY,
        account_id="cash",
    )
    reduction = CandidateReduction(
        patch=CandidatePatch(spending_category_id=None),
        candidate=candidate,
        blocking_ambiguities=(ambiguity,),
    )
    trace = ContributionProcessingTrace(
        analysis_path=ContributionAnalysisPath.MODEL_PIPELINE,
        extraction=ContributionExtraction(),
        semantic_interpretation=SemanticInterpretation(),
        grounded_interpretation=GroundedInterpretation(ambiguities=(ambiguity,)),
        candidate_reduction=reduction,
    )
    validator = StubValidator()
    wallet = StubWallet()
    workflow = CaptureWorkflow(
        processor=FixedProcessor(ContributionProcessingResult(candidate, trace)),
        validator=validator,
        wallet=wallet,
        today=lambda: TODAY,
        generate_capture_id=lambda: "capture_1",
    )

    result = workflow.receive(UserContribution("Coffee"))

    assert result.outcome is CaptureOutcome.AWAITING_INTERACTION
    assert result.session.pending_interaction == PendingInteraction(
        kind=PendingInteractionKind.DISAMBIGUATE,
        field=CandidateField.SPENDING_CATEGORY_ID,
        options=(
            InteractionOption("food_coffee", "Food > Coffee"),
            InteractionOption("work_coffee", "Work > Coffee"),
        ),
    )
    assert result.processing_trace is trace
    assert validator.calls == []
    assert wallet.calls == []


def test_unresolved_replacement_is_corrected_before_normal_assessment() -> None:
    unresolved = UnresolvedField(
        field=CandidateField.ACCOUNT_ID,
        evidence=SourceEvidence(0, 15, "Mystery account"),
        reason="not selectable",
    )
    candidate = TransactionCandidate(
        type=TransactionType.EXPENSE,
        amount_minor=3500,
        occurred_on=TODAY,
        spending_category_id="coffee",
    )
    reduction = CandidateReduction(
        patch=CandidatePatch(account_id=None),
        candidate=candidate,
        blocking_unresolved_fields=(unresolved,),
    )
    trace = ContributionProcessingTrace(
        analysis_path=ContributionAnalysisPath.MODEL_PIPELINE,
        extraction=ContributionExtraction(),
        semantic_interpretation=SemanticInterpretation(),
        grounded_interpretation=GroundedInterpretation(unresolved_fields=(unresolved,)),
        candidate_reduction=reduction,
    )
    validator = StubValidator()
    wallet = StubWallet()
    workflow = CaptureWorkflow(
        processor=FixedProcessor(ContributionProcessingResult(candidate, trace)),
        validator=validator,
        wallet=wallet,
        today=lambda: TODAY,
        generate_capture_id=lambda: "capture_1",
    )

    result = workflow.receive(UserContribution("Mystery account"))

    assert result.session.pending_interaction == PendingInteraction(
        kind=PendingInteractionKind.CORRECT,
        field=CandidateField.ACCOUNT_ID,
    )
    assert validator.calls == []
    assert wallet.calls == []


@pytest.mark.parametrize("issue_stage", ["extraction", "semantic"])
def test_analysis_issue_preserves_candidate_and_requests_general_clarification(
    issue_stage: str,
) -> None:
    candidate = TransactionCandidate(
        type=TransactionType.EXPENSE,
        amount_minor=3500,
        occurred_on=TODAY,
        account_id="cash",
        spending_category_id="coffee",
    )
    extraction = ContributionExtraction(
        issues=(ExtractionIssue(MentionKind.REFERENCE, "invented", "not source-grounded"),)
        if issue_stage == "extraction"
        else ()
    )
    semantic = SemanticInterpretation(
        issues=(SemanticIssue("incompatible role"),) if issue_stage == "semantic" else ()
    )
    reduction = CandidateReduction(patch=CandidatePatch(), candidate=candidate)
    trace = ContributionProcessingTrace(
        analysis_path=ContributionAnalysisPath.MODEL_PIPELINE,
        extraction=extraction,
        semantic_interpretation=semantic,
        grounded_interpretation=GroundedInterpretation(),
        candidate_reduction=reduction,
    )
    validator = StubValidator()
    wallet = StubWallet()
    workflow = CaptureWorkflow(
        processor=FixedProcessor(ContributionProcessingResult(candidate, trace)),
        validator=validator,
        wallet=wallet,
        today=lambda: TODAY,
        generate_capture_id=lambda: "capture_1",
    )

    result = workflow.receive(UserContribution("correction"))

    assert result.session.candidate == candidate
    assert result.session.pending_interaction == PendingInteraction(
        kind=PendingInteractionKind.CLARIFY
    )
    assert validator.calls == []
    assert wallet.calls == []


def test_capture_sessions_belong_to_the_workflow_that_created_them() -> None:
    first_workflow, _, _, _ = _workflow(
        {
            "Record an expense": interpretation_patch(
                patch=CandidatePatch(type=TransactionType.EXPENSE)
            )
        }
    )
    second_workflow, _, _, _ = _workflow({})
    first = first_workflow.receive(UserContribution("Record an expense"))

    with pytest.raises(CaptureSessionNotFoundError, match=first.session.id):
        second_workflow.receive(
            UserContribution("not interpreted"),
            capture_id=first.session.id,
        )


def test_unknown_capture_is_rejected() -> None:
    workflow, _, _, _ = _workflow({})

    with pytest.raises(CaptureSessionNotFoundError, match="missing_capture"):
        workflow.receive(
            UserContribution("not interpreted"),
            capture_id="missing_capture",
        )


def _workflow(
    interpretations: dict[str, CandidatePatch],
    *,
    rejected_fields: list[CandidateField | None] | None = None,
    wallet_failures: list[Exception] | None = None,
) -> tuple[CaptureWorkflow, StubProcessor, StubValidator, StubWallet]:
    processor = StubProcessor(interpretations)
    validator = StubValidator(rejected_fields=list(rejected_fields or []))
    wallet = StubWallet(failures=list(wallet_failures or []))
    workflow = CaptureWorkflow(
        processor=processor,
        validator=validator,
        wallet=wallet,
        today=lambda: TODAY,
        generate_capture_id=lambda: "capture_1",
    )
    return workflow, processor, validator, wallet
