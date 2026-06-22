"""
Shared types for forecast ingestion services.
"""

from dataclasses import dataclass, field


@dataclass
class IngestResult:
    """
    Aggregated outcome of a forecast ingestion run.

    Attributes:
        saved: Number of forecast periods successfully written to the database.
        skipped: Number of periods skipped due to missing data or errors.
        errors: List of human-readable error messages encountered during the run.
    """

    saved: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
