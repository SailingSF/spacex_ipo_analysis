"""SpaceX S-1 analysis package.

Modules:
  data    -- load the extracted CSVs (../csv) into pandas DataFrames + helpers
  charts  -- matplotlib styling and thin chart-helper wrappers
  dcf     -- scaffolding for the segment-level DCF valuation model

Nothing here computes analysis or renders charts on import; these are building
blocks to be called from notebooks/scripts once we start the actual work.
"""

from . import data, charts, dcf  # noqa: F401

__all__ = ["data", "charts", "dcf"]
