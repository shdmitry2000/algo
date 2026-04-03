import csv
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from datagathering.models import StandardOptionTick
from datagathering.providers.base_provider import BaseProvider

_FILENAME_RE = re.compile(r"^([a-zA-Z0-9]+)_(\d{4}-\d{2}-\d{2})_(\d{2}:\d{2})\.csv$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def resolve_chain_files_dir(config_value: str, project_root: str) -> Path:
    if not config_value:
        raise ValueError("CHAIN_FILES_DIR is not configured")
    path = Path(config_value)
    if not path.is_absolute():
        path = Path(project_root) / path
    return path.resolve()


def scan_inventory(base_dir: Path) -> Dict[str, Dict[str, List[str]]]:
    by_ticker: Dict[str, Dict[str, List[str]]] = {}
    if not base_dir.exists() or not base_dir.is_dir():
        return by_ticker

    for file_path in base_dir.glob("*.csv"):
        parsed = parse_filename(file_path.name)
        if not parsed:
            continue
        ticker, date_str, time_str = parsed
        by_ticker.setdefault(ticker, {}).setdefault(date_str, []).append(time_str)

    for ticker in by_ticker:
        for date_str in by_ticker[ticker]:
            by_ticker[ticker][date_str] = sorted(set(by_ticker[ticker][date_str]))
        by_ticker[ticker] = dict(sorted(by_ticker[ticker].items(), reverse=True))

    return dict(sorted(by_ticker.items()))


def parse_filename(filename: str) -> Tuple[str, str, str] | None:
    m = _FILENAME_RE.match(filename)
    if not m:
        return None
    ticker_raw, date_str, time_str = m.groups()
    return ticker_raw.upper(), date_str, time_str


def build_filename(ticker: str, date_str: str, time_str: str) -> str:
    ticker_norm = ticker.strip().lower()
    if not ticker_norm or not re.fullmatch(r"[a-z0-9]+", ticker_norm):
        raise ValueError("Invalid ticker format")
    if not _DATE_RE.fullmatch(date_str):
        raise ValueError("Invalid date format")
    if not _TIME_RE.fullmatch(time_str):
        raise ValueError("Invalid time format")
    return f"{ticker_norm}_{date_str}_{time_str}.csv"


def resolve_inventory_file(base_dir: Path, ticker: str, date_str: str, time_str: str) -> Path:
    filename = build_filename(ticker, date_str, time_str)
    target = (base_dir / filename).resolve()
    base_real = base_dir.resolve()
    if os.path.commonpath([str(base_real), str(target)]) != str(base_real):
        raise ValueError("Resolved path is outside CHAIN_FILES_DIR")
    if not target.is_file():
        raise FileNotFoundError(f"File not found: {filename}")
    return target


def filename_updated_at_iso(date_str: str, time_str: str) -> str:
    dt = datetime.strptime(f"{date_str}_{time_str}", "%Y-%m-%d_%H:%M").replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _map_right(raw_right: str) -> str:
    v = str(raw_right).strip().lower()
    if v == "call":
        return "C"
    if v == "put":
        return "P"
    raise ValueError(f"Unsupported right value: {raw_right}")


def load_ticks_from_csv(csv_path: Path, provider_name: str = "file_folder") -> List[StandardOptionTick]:
    ticks: List[StandardOptionTick] = []

    def _to_int(value) -> int:
        if value is None:
            return 0
        s = str(value).strip()
        if not s:
            return 0
        return int(float(s))

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            right = _map_right(row.get("right", ""))
            tick = StandardOptionTick.make(
                root=row.get("ticker", ""),
                expiration=row.get("expiration", ""),
                strike=row.get("strike", 0),
                right=right,
                bid=row.get("bid", 0),
                ask=row.get("ask", 0),
                volume=_to_int(row.get("volume", 0)),
                open_interest=_to_int(row.get("openInterest", 0)),
                provider=provider_name,
            )
            last_trade = (row.get("lastTradeDate") or "").strip()
            if last_trade:
                tick.timestamp = last_trade
            ticks.append(tick)
    return ticks


class FileFolderProvider(BaseProvider):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    @property
    def name(self) -> str:
        return "file_folder"

    def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
        ticker_u = ticker.upper()
        inventory = scan_inventory(self.base_dir)
        dates = inventory.get(ticker_u, {})
        if not dates:
            return []

        latest_date = sorted(dates.keys(), reverse=True)[0]
        latest_time = sorted(dates[latest_date], reverse=True)[0]
        csv_path = resolve_inventory_file(self.base_dir, ticker_u, latest_date, latest_time)
        return load_ticks_from_csv(csv_path, provider_name=self.name)
