from __future__ import annotations

import os
from typing import Optional


SPREADSHEET_ID: str = os.environ.get(
    "SPREADSHEET_ID",
    "1yXzUII6pZ9rg57C0c7gefl57z88uz1_mKlNBy8Nu4g0",
)
SHEET_NAME: str = os.environ.get("SHEET_NAME", "Объявления")
DRY_RUN: bool = os.environ.get("DRY_RUN", "false").lower() == "true"
OUTPUT_JSON: Optional[str] = os.environ.get("OUTPUT_JSON")
