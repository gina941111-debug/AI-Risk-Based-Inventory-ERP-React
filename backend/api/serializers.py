from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd


def jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if hasattr(value, "item"):
        try:
            return jsonable(value.item())
        except Exception:
            pass
    if pd.isna(value) if not isinstance(value, (str, bytes, list, tuple, dict)) else False:
        return None
    return value


def records(frame: Any) -> list[dict[str, Any]]:
    if frame is None:
        return []
    if isinstance(frame, pd.DataFrame):
        return jsonable(frame.where(pd.notna(frame), None).to_dict(orient="records"))
    if isinstance(frame, list):
        return jsonable(frame)
    return jsonable(frame)
