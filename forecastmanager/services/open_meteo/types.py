"""
Shared types for the Open-Meteo connector.

``IngestResult`` now lives in ``forecastmanager.services.types`` so it can be
shared across providers. Re-exported here for backwards compatibility.
"""

from forecastmanager.services.types import IngestResult

__all__ = ["IngestResult"]
