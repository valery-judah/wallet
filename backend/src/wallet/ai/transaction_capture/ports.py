from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Protocol

from wallet.ai.transaction_capture.domain import (
    CandidateField,
    PendingInteraction,
    TransactionCandidate,
    UserContribution,
)
from wallet.domain.transactions import Transaction

if TYPE_CHECKING:
    from wallet.ai.transaction_capture.processing import ContributionProcessingResult


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
class CaptureAccountReference:
    """Trusted selectable account metadata safe for interpretation."""

    id: str
    label: str
    currency: str


@dataclass(frozen=True, slots=True)
class CaptureCategoryReference:
    """Trusted category identifier paired with its full user-facing path."""

    id: str
    label: str


@dataclass(frozen=True, slots=True)
class CaptureReferenceCatalog:
    """Wallet-owned references that may be selected during transaction capture."""

    accounts: tuple[CaptureAccountReference, ...]
    spending_categories: tuple[CaptureCategoryReference, ...]
    income_categories: tuple[CaptureCategoryReference, ...]


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
    def execute(
        self,
        candidate: TransactionCandidate,
        *,
        operation_id: str,
    ) -> Transaction:
        """Idempotently create and return a Wallet transaction."""
