from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Protocol

from wallet.ai.transaction_capture.domain import (
    CandidateField,
    PendingInteraction,
    TransactionCandidate,
    UserContribution,
)

if TYPE_CHECKING:
    from wallet.ai.transaction_capture.processing import ContributionProcessingResult


CaptureIdGenerator = Callable[[], str]


class ContributionProcessor(Protocol):
    def process(
        self,
        contribution: UserContribution,
        *,
        candidate: TransactionCandidate,
        pending_interaction: PendingInteraction | None,
        on_date: date,
    ) -> ContributionProcessingResult:
        """Process one contribution against current dialogue state."""
        ...


@dataclass(frozen=True, slots=True)
class CaptureReference:
    """Trusted wallet identifier paired with its user-facing selection label."""

    id: str
    label: str


@dataclass(frozen=True, slots=True)
class CaptureReferenceCatalog:
    """Wallet-owned references that may be selected during transaction capture."""

    accounts: tuple[CaptureReference, ...]
    spending_categories: tuple[CaptureReference, ...]
    income_categories: tuple[CaptureReference, ...]


class CaptureReferenceProvider(Protocol):
    def capture_references(self) -> CaptureReferenceCatalog:
        """Return the currently selectable wallet references."""
        ...


class ContributionProcessorFactory(Protocol):
    def build(
        self,
        *,
        references: CaptureReferenceProvider,
    ) -> ContributionProcessor:
        """Build a processor bound to one capture workflow's dependencies."""
        ...


class CandidateValidator(Protocol):
    def invalid_field(self, candidate: TransactionCandidate) -> CandidateField | None:
        """Return the first contextually invalid field, if one exists."""
        ...


class WalletTransactionExecutor(Protocol):
    def execute(self, candidate: TransactionCandidate) -> str:
        """Create a Wallet transaction and return its identifier."""
