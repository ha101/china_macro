from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests import Response
from urllib3.exceptions import InsecureRequestWarning


requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "snapshot.js"

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
)


def fetch(url: str, *, verify: bool = True) -> Response:
    last_error: Exception | None = None
    for _ in range(3):
        try:
            response = SESSION.get(url, timeout=(20, 90), verify=verify)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
    raise last_error if last_error else RuntimeError(f"Unable to fetch {url}")


def soup_from_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def clean_text(value: str) -> str:
    normalized = (
        value.replace("\xa0", " ")
        .replace("\u3000", " ")
        .replace("\u2002", " ")
        .replace("（", "(")
        .replace("）", ")")
    )
    return re.sub(r"\s+", " ", normalized).strip()


def article_text(soup: BeautifulSoup) -> str:
    node = (
        soup.select_one(".TRS_Editor")
        or soup.select_one(".content")
        or soup.select_one("#zoom")
        or soup.body
    )
    return clean_text(node.get_text(" ", strip=True)) if node else ""


def read_tables_from_html(html: str) -> list[pd.DataFrame]:
    return pd.read_html(StringIO(html), flavor="lxml")


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        if value.is_integer():
            return str(int(value))
    return clean_text(str(value))


def dataframe_payload(df: pd.DataFrame, title: str) -> dict[str, Any]:
    safe = df.fillna("")
    return {
        "title": title,
        "headers": [stringify(column) for column in safe.columns.tolist()],
        "rows": [[stringify(cell) for cell in row] for row in safe.values.tolist()],
    }


def source_snapshot(
    *,
    source_id: str,
    release_id: str,
    title: str,
    date: str,
    url: str,
    summary: str,
    highlights: list[str],
    tables: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "sourceId": source_id,
        "releaseId": release_id,
        "title": title,
        "date": date,
        "url": url,
        "summary": summary,
        "highlights": highlights,
        "tables": tables or [],
    }


def add_status_snapshot(
    snapshot: dict[str, Any],
    *,
    source_id: str,
    release_id: str,
    title: str,
    date: str,
    url: str,
    summary: str,
    highlights: list[str],
) -> None:
    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id=source_id,
            release_id=release_id,
            title=title,
            date=date,
            url=url,
            summary=summary,
            highlights=highlights,
            tables=[],
        )
    )


def metric_entry(
    *,
    value: str,
    secondary: str = "",
    date: str,
    period: str,
    source_id: str,
    source_title: str,
    source_url: str,
) -> dict[str, str]:
    return {
        "value": value,
        "secondary": secondary,
        "date": date,
        "period": period,
        "sourceId": source_id,
        "sourceTitle": source_title,
        "sourceUrl": source_url,
    }


def format_percent(value: float | str) -> str:
    numeric = float(str(value).replace("%", ""))
    return f"{numeric:.1f}%"


def format_pp(value: float | str) -> str:
    numeric = float(str(value).replace("%", ""))
    return f"{numeric:.2f} pp"


def format_trillion_yuan(value: float | str) -> str:
    numeric = float(str(value))
    return f"RMB {numeric:.2f} tn"


def format_billion_yuan(value: float | str) -> str:
    numeric = float(str(value))
    return f"RMB {numeric:.1f} bn"


def format_billion_usd(value: float | str) -> str:
    numeric = float(str(value))
    return f"USD {numeric:.1f} bn"


def format_trillion_usd(value: float | str) -> str:
    numeric = float(str(value))
    return f"USD {numeric:.4f} tn"


def from_100m_yuan(value: float | str) -> str:
    numeric = float(str(value))
    return f"RMB {numeric / 10:.1f} bn"


def from_100m_usd(value: float | str) -> str:
    numeric = float(str(value))
    return f"USD {numeric / 100:.1f} bn"


def from_10k_sqm(value: float | str) -> str:
    numeric = float(str(value))
    return f"{numeric / 100:.2f} mn sq m"


def from_10k_units(value: float | str) -> str:
    numeric = float(str(value))
    return f"{numeric / 10000:.3f} mn units"


def row_lookup(df: pd.DataFrame) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        label = stringify(row.iloc[0])
        if not label:
            continue
        records[label] = {
            "c1": stringify(row.iloc[1]) if len(row) > 1 else "",
            "c2": stringify(row.iloc[2]) if len(row) > 2 else "",
            "c3": stringify(row.iloc[3]) if len(row) > 3 else "",
            "c4": stringify(row.iloc[4]) if len(row) > 4 else "",
        }
    return records


def row_lookup_contains(records: dict[str, dict[str, str]], needle: str) -> dict[str, str] | None:
    lowered = needle.lower()
    for label, record in records.items():
        if lowered in label.lower():
            return record
    return None


def find_row_in_tables(
    tables: list[pd.DataFrame],
    label: str,
    *,
    unit_contains: str | None = None,
) -> dict[str, str] | None:
    lowered_label = label.lower()
    lowered_unit = unit_contains.lower() if unit_contains else None
    for table in tables:
        for _, row in table.iterrows():
            row_label = stringify(row.iloc[0])
            if lowered_label not in row_label.lower():
                continue
            unit = stringify(row.iloc[1]) if len(row) > 1 else ""
            if lowered_unit and lowered_unit not in unit.lower():
                continue
            return {
                "label": row_label,
                "unit": unit,
                "value": stringify(row.iloc[2]) if len(row) > 2 else "",
                "change": stringify(row.iloc[3]) if len(row) > 3 else "",
                "extra": stringify(row.iloc[4]) if len(row) > 4 else "",
            }
    return None


def first_match(text: str, patterns: list[str]) -> re.Match[str] | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match
    return None


def parse_float(value: Any) -> float | None:
    text = stringify(value).replace(",", "")
    if not text:
        return None
    match = re.search(r"-?[\d.]+", text)
    if not match:
        return None
    return float(match.group(0))


def add_history_point(
    snapshot: dict[str, Any],
    *,
    metric_name: str,
    value: str,
    numeric: float | None,
    date: str,
    period: str,
    source_id: str,
    source_title: str,
    source_url: str,
    secondary: str = "",
) -> None:
    history = snapshot.setdefault("history", {})
    history.setdefault(metric_name, []).append(
        {
            "value": value,
            "numeric": numeric,
            "date": date,
            "period": period,
            "secondary": secondary,
            "sourceId": source_id,
            "sourceTitle": source_title,
            "sourceUrl": source_url,
        }
    )


def history_has_period(snapshot: dict[str, Any], metric_name: str, period: str) -> bool:
    return any(
        str(point.get("period", "")) == str(period)
        for point in snapshot.get("history", {}).get(metric_name, [])
    )


def latest_release_date(url: str) -> str:
    html = fetch(url).text
    soup = soup_from_html(html)
    meta = soup.find("meta", attrs={"name": "PubDate"})
    if meta and meta.get("content"):
        return clean_text(meta["content"])
    match = re.search(r"t(20\d{2})(\d{2})(\d{2})_", url)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    match = re.search(r"/(20\d{2})(\d{2})/", url)
    if match:
        return f"{match.group(1)}-{match.group(2)}-01"
    return datetime.now(timezone.utc).date().isoformat()


def page_pub_date(soup: BeautifulSoup, url: str) -> str:
    meta = soup.find("meta", attrs={"name": "PubDate"})
    if meta and meta.get("content"):
        return clean_text(meta["content"])
    text = clean_text(soup.get_text(" ", strip=True))
    match = re.search(r"公开日期[:：]?\s*(20\d{2})年(\d{1,2})月(\d{1,2})日", text)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    match = re.search(r"t(20\d{2})(\d{2})(\d{2})_", url)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    match = re.search(r"/(20\d{2})(\d{2})/", url)
    if match:
        return f"{match.group(1)}-{match.group(2)}-01"
    return datetime.now(timezone.utc).date().isoformat()


def signed_percent(direction: str, value: str) -> str:
    numeric = float(value)
    prefix = "+" if direction == "增长" else "-"
    return f"{prefix}{numeric:.1f}%"


def strip_release_prefix(title: str) -> str:
    return re.sub(r"^\d+\.", "", clean_text(title)).strip()


def crawl_nbs_press_releases() -> list[dict[str, str]]:
    base = "https://www.stats.gov.cn/english/PressRelease/"
    first_page_html = fetch(base).text
    count_match = re.search(r"countPage\s*=\s*(\d+)", first_page_html)
    page_count = int(count_match.group(1)) if count_match else 1
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=370)).isoformat()
    releases: list[dict[str, str]] = []
    seen: set[str] = set()

    for page_index in range(page_count):
        page_url = base + ("index.html" if page_index == 0 else f"index_{page_index}.html")
        html = first_page_html if page_index == 0 else fetch(page_url).text
        soup = soup_from_html(html)
        page_items: list[dict[str, str]] = []
        for anchor in soup.select("ul.list li a, .list_box a, .news_list a, .list a"):
            href = anchor.get("href")
            if not href:
                continue
            title = strip_release_prefix(anchor.get_text(" ", strip=True))
            if not title:
                continue
            full_url = urljoin(page_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            item = {"title": title, "url": full_url}
            releases.append(item)
            page_items.append(item)

        page_months = [
            f"{match.group(1)}-{match.group(2)}-01"
            for item in page_items
            if (match := re.search(r"/(20\d{2})(\d{2})/", item["url"]))
        ]
        if page_months and max(page_months) < cutoff:
            break

    return releases


def select_nbs_releases(
    releases: list[dict[str, str]],
    *,
    title_fragment: str,
    limit: int = 12,
) -> list[dict[str, str]]:
    selected = [item for item in releases if title_fragment.lower() in item["title"].lower()]
    return selected[:limit]


def latest_nbs_release_url(title_fragment: str, fallback_url: str) -> str:
    try:
        releases = crawl_nbs_press_releases()
        selected = select_nbs_releases(releases, title_fragment=title_fragment, limit=1)
        if selected:
            return selected[0]["url"]
    except Exception:
        pass
    return fallback_url


def ytd_label_from_table(df: pd.DataFrame) -> str:
    if df.empty or len(df.columns) < 4:
        return "YTD avg"
    header = stringify(df.iloc[0, 3])
    match = re.search(r"(Jan-[A-Za-z]{3,9})", header, re.I)
    if match:
        return f"{match.group(1)} avg"
    return "YTD avg"


def sort_history(snapshot: dict[str, Any]) -> None:
    for metric_name, points in (snapshot.get("history") or {}).items():
        points.sort(key=lambda item: (str(item.get("date", "")), str(item.get("period", ""))))


def backfill_metrics_from_history(snapshot: dict[str, Any]) -> None:
    for metric_name, points in (snapshot.get("history") or {}).items():
        if metric_name in snapshot["metrics"] or not points:
            continue
        latest = sorted(points, key=lambda item: (str(item.get("date", "")), str(item.get("period", ""))))[-1]
        snapshot["metrics"][metric_name] = metric_entry(
            value=latest["value"],
            secondary=latest.get("secondary", ""),
            date=latest["date"],
            period=latest["period"],
            source_id=latest["sourceId"],
            source_title=latest["sourceTitle"],
            source_url=latest["sourceUrl"],
        )


MONTH_NUMBERS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def month_label_to_iso(label: str, current_year: int | None = None) -> tuple[str, int | None]:
    cleaned = clean_text(label).replace("‑", "-")
    year = current_year
    month_label = cleaned
    if "-" in cleaned:
        maybe_year, maybe_month = cleaned.split("-", 1)
        if maybe_year.isdigit():
            year = int(maybe_year)
            month_label = maybe_month
    month = MONTH_NUMBERS.get(month_label.lower())
    if year is None or month is None:
        return cleaned, year
    return f"{year:04d}-{month:02d}-01", year


def period_from_title(title: str) -> str:
    match = re.search(
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)[^,]*\d{4}|Q\d[^,]*\d{4}|H1 \d{4}|2025|2026)",
        title,
        re.I,
    )
    return clean_text(match.group(1)) if match else clean_text(title)


def english_month_year_to_iso(label: str) -> str:
    cleaned = clean_text(label)
    match = re.search(r"([A-Za-z]{3,9})\s+(\d{4})", cleaned)
    if not match:
        return cleaned
    month = MONTH_NUMBERS.get(match.group(1).lower())
    if month is None:
        return cleaned
    return f"{int(match.group(2)):04d}-{month:02d}-01"


def ceic_page_payload(url: str) -> tuple[str, str]:
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True)) if soup.title else "CEIC data page"
    description_node = soup.find("meta", attrs={"name": "description"})
    description = clean_text(description_node["content"]) if description_node else ""
    return title, description


def parse_ceic_description(description: str) -> dict[str, str] | None:
    match = re.search(
        (
            r"data was reported at ([\d,.\-]+)\s+(.+?) in ([A-Za-z]{3,9} \d{4})\."
            r"\s+This records (?:an|a) (increase|decrease) from the previous number of "
            r"([\d,.\-]+)\s+(.+?) for ([A-Za-z]{3,9} \d{4})\."
        ),
        description,
        re.I,
    )
    if not match:
        return None
    latest, latest_unit, latest_period, direction, previous, previous_unit, previous_period = match.groups()
    return {
        "latest": latest,
        "latest_unit": latest_unit,
        "latest_period": latest_period,
        "direction": direction,
        "previous": previous,
        "previous_unit": previous_unit,
        "previous_period": previous_period,
    }


def format_ceic_value(raw_value: str, unit: str) -> str:
    numeric = float(raw_value.replace(",", ""))
    normalized = clean_text(unit)
    if normalized == "%":
        return f"{numeric:.1f}%"
    if normalized == "USD th":
        return format_billion_usd(numeric / 1_000_000)
    if normalized == "Ton th":
        return f"{numeric / 1000:.2f} mn t"
    if normalized == "Ton tt":
        return f"{numeric / 100:.2f} mn t"
    if normalized == "sq m th":
        return f"{numeric / 1000:.2f} mn sq m"
    return f"{numeric:,.3f} {normalized}"


def append_metric_from_ceic(
    snapshot: dict[str, Any],
    *,
    metric_name: str,
    url: str,
    source_id: str,
    secondary_prefix: str = "",
    value_suffix: str = "",
) -> dict[str, str] | None:
    title, description = ceic_page_payload(url)
    parsed = parse_ceic_description(description)
    if not parsed:
        return None

    latest_value = format_ceic_value(parsed["latest"], parsed["latest_unit"]) + value_suffix
    previous_value = format_ceic_value(parsed["previous"], parsed["previous_unit"]) + value_suffix
    iso_date = english_month_year_to_iso(parsed["latest_period"])
    secondary = f"{parsed['previous_period']}: {previous_value}"
    if secondary_prefix:
        secondary = f"{secondary_prefix}; {secondary}" if secondary else secondary_prefix

    snapshot["metrics"][metric_name] = metric_entry(
        value=latest_value,
        secondary=secondary,
        date=iso_date,
        period=parsed["latest_period"],
        source_id=source_id,
        source_title=title,
        source_url=url,
    )
    add_history_point(
        snapshot,
        metric_name=metric_name,
        value=latest_value,
        numeric=parse_float(parsed["latest"]),
        date=iso_date,
        period=parsed["latest_period"],
        source_id=source_id,
        source_title=title,
        source_url=url,
        secondary=secondary_prefix or "Latest point from CEIC page metadata",
    )
    add_history_point(
        snapshot,
        metric_name=metric_name,
        value=previous_value,
        numeric=parse_float(parsed["previous"]),
        date=english_month_year_to_iso(parsed["previous_period"]),
        period=parsed["previous_period"],
        source_id=source_id,
        source_title=title,
        source_url=url,
        secondary=secondary_prefix or "Previous point from CEIC page metadata",
    )
    return {"title": title, "description": description, "url": url}



def extract_nbs_70_city(snapshot: dict[str, Any]) -> None:
    url = latest_nbs_release_url(
        "Sales Prices of Commercial Residential Buildings",
        "https://www.stats.gov.cn/english/PressRelease/202602/t20260213_1962622.html",
    )
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(
        soup.find("meta", attrs={"name": "ArticleTitle"})["content"]
        if soup.find("meta", attrs={"name": "ArticleTitle"})
        else soup.title.get_text(" ", strip=True)
    )
    date = soup.find("meta", attrs={"name": "PubDate"})["content"]
    tables = read_tables_from_html(html)
    period_label = period_from_title(title)

    def parse_city_table(df: pd.DataFrame) -> list[dict[str, float | str]]:
        rows = []
        for idx in range(2, len(df)):
            values = [stringify(value) for value in df.iloc[idx].tolist()]
            for offset in (0, 3):
                city = values[offset]
                if not city or city.lower().startswith("note"):
                    continue
                rows.append(
                    {
                        "city": city,
                        "mom": float(values[offset + 1]),
                        "yoy": float(values[offset + 2]),
                    }
                )
        return rows

    new_home_rows = parse_city_table(tables[0])
    existing_home_rows = parse_city_table(tables[1])

    def avg(values: list[dict[str, float | str]], field: str) -> float:
        return sum(float(item[field]) for item in values) / len(values)

    def direction_counts(values: list[dict[str, float | str]]) -> tuple[int, int, int]:
        up = sum(1 for item in values if float(item["mom"]) > 100)
        flat = sum(1 for item in values if float(item["mom"]) == 100)
        down = sum(1 for item in values if float(item["mom"]) < 100)
        return up, flat, down

    new_up, new_flat, new_down = direction_counts(new_home_rows)
    existing_up, existing_flat, existing_down = direction_counts(existing_home_rows)

    snapshot["metrics"]["70-city new home price index"] = metric_entry(
        value=f"Avg M/M {avg(new_home_rows, 'mom'):.2f}",
        secondary=(
            f"Avg Y/Y {avg(new_home_rows, 'yoy'):.2f}; "
            f"{new_up} up / {new_flat} flat / {new_down} down"
        ),
        date=date,
        period=period_label,
        source_id="nbs-70city",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["70-city existing home price index"] = metric_entry(
        value=f"Avg M/M {avg(existing_home_rows, 'mom'):.2f}",
        secondary=(
            f"Avg Y/Y {avg(existing_home_rows, 'yoy'):.2f}; "
            f"{existing_up} up / {existing_flat} flat / {existing_down} down"
        ),
        date=date,
        period=period_label,
        source_id="nbs-70city",
        source_title=title,
        source_url=url,
    )

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="nbs-70city",
            release_id="nbs-70city-2026-01",
            title=title,
            date=date,
            url=url,
            summary="Full 70-city tables for newly constructed and second-hand residential prices.",
            highlights=[
                snapshot["metrics"]["70-city new home price index"]["value"]
                + " | "
                + snapshot["metrics"]["70-city new home price index"]["secondary"],
                snapshot["metrics"]["70-city existing home price index"]["value"]
                + " | "
                + snapshot["metrics"]["70-city existing home price index"]["secondary"],
                "This is the latest accessible English 70-city release in the current snapshot.",
            ],
            tables=[
                dataframe_payload(tables[0], "Newly Constructed Residential Prices"),
                dataframe_payload(tables[1], "Second-Hand Residential Prices"),
                dataframe_payload(tables[2], "Newly Constructed Residential Prices by Size"),
                dataframe_payload(tables[3], "Second-Hand Residential Prices by Size"),
            ],
        )
    )


def extract_nbs_property(snapshot: dict[str, Any]) -> None:
    url = "https://www.stats.gov.cn/english/PressRelease/202603/t20260317_1962803.html"
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True))
    date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
    tables = read_tables_from_html(html)
    rows = row_lookup(tables[0])

    mapping = {
        "Real estate investment": (
            "Investment in real estate development (100 million yuan)",
            from_100m_yuan,
        ),
        "Property sales by floor area": (
            "Floor space of newly built commercial buildings sold (10,000 sq.m)",
            from_10k_sqm,
        ),
        "Property sales by value": (
            "Sales of newly built commercial buildings (100 million yuan)",
            from_100m_yuan,
        ),
        "Housing starts": ("Floor space of buildings newly started (10,000 sq.m)", from_10k_sqm),
        "Construction under way": (
            "Floor space of buildings under construction (10,000 sq.m)",
            from_10k_sqm,
        ),
        "Completions": ("Floor space of buildings completed (10,000 sq.m)", from_10k_sqm),
        "Funds available to developers": (
            "Funds for investment this year for real estate development enterprises (100 million yuan)",
            from_100m_yuan,
        ),
    }

    for metric_name, (label, formatter) in mapping.items():
        row = rows.get(label)
        if not row:
            continue
        snapshot["metrics"][metric_name] = metric_entry(
            value=formatter(row["c1"]),
            secondary=f"{row['c2']}% y/y",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="nbs-releases",
            release_id="nbs-property-2026-02",
            title=title,
            date=date,
            url=url,
            summary="Latest property-development, sales, starts, completions, and developer funding table.",
            highlights=[
                f"Real estate investment: {snapshot['metrics'].get('Real estate investment', {}).get('value', 'n/a')}",
                f"Floor area sold: {snapshot['metrics'].get('Property sales by floor area', {}).get('value', 'n/a')}",
                f"Funds available to developers: {snapshot['metrics'].get('Funds available to developers', {}).get('value', 'n/a')}",
            ],
            tables=[
                dataframe_payload(tables[0], "Real Estate Development and Sales"),
                dataframe_payload(tables[1], "Regional Real Estate Investment"),
                dataframe_payload(tables[2], "Regional Sales"),
            ],
        )
    )


def extract_nbs_activity(snapshot: dict[str, Any]) -> None:
    url = "https://www.stats.gov.cn/english/PressRelease/202603/t20260316_1962783.html"
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True))
    date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
    text = article_text(soup)

    trade_match = re.search(
        (
            r"total value of imports and exports of goods was ([\d,.]+) billion yuan, up by ([\d.]+) percent.*?"
            r"value of exports was ([\d,.]+) billion yuan, up by ([\d.]+) percent, and the value of imports was "
            r"([\d,.]+) billion yuan, up by ([\d.]+) percent"
        ),
        text,
        re.I,
    )
    unemployment_match = re.search(
        (
            r"In February, the urban surveyed unemployment rate was ([\d.]+) percent.*?"
            r"urban surveyed unemployment rate in 31 major cities was ([\d.]+) percent.*?"
            r"worked ([\d.]+) hours per week on average"
        ),
        text,
        re.I,
    )
    service_match = re.search(
        r"Index of Services Production grew by ([\d.]+) percent year on year",
        text,
        re.I,
    )
    high_tech_match = re.search(
        r"value added of equipment manufacturing increased by ([\d.]+) percent year on year and that of high-tech manufacturing increased by ([\d.]+) percent",
        text,
        re.I,
    )

    if trade_match:
        total_trade, total_growth, exports, exports_growth, imports, imports_growth = trade_match.groups()
        snapshot["metrics"]["Exports (goods, RMB)"] = metric_entry(
            value=format_billion_yuan(float(exports.replace(",", ""))),
            secondary=f"{exports_growth}% y/y (goods exports, CNY terms)",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )
        trade_balance = float(exports.replace(",", "")) - float(imports.replace(",", ""))
        snapshot["metrics"]["Trade balance"] = metric_entry(
            value=format_billion_yuan(trade_balance),
            secondary="Goods trade balance, CNY terms",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )
        mech_match = re.search(r"exports of mechanical and electrical products went up by ([\d.]+) percent", text, re.I)
        if mech_match:
            snapshot["metrics"]["Exports of machinery and electronics"] = metric_entry(
                value=f"{mech_match.group(1)}% y/y",
                secondary="Official NBS summary of mechanical and electrical exports",
                date=date,
                period="Jan-Feb 2026",
                source_id="nbs-releases",
                source_title=title,
                source_url=url,
            )
        snapshot["metrics"]["Imports (goods, RMB)"] = metric_entry(
            value=format_billion_yuan(float(imports.replace(",", ""))),
            secondary=f"{imports_growth}% y/y (goods imports, CNY terms)",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    if unemployment_match:
        urban_unemployment, unemployment_31, hours_worked = unemployment_match.groups()
        snapshot["metrics"]["Urban surveyed unemployment"] = metric_entry(
            value=format_percent(urban_unemployment),
            secondary="February rate",
            date=date,
            period="February 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["31-city unemployment"] = metric_entry(
            value=format_percent(unemployment_31),
            secondary="February rate",
            date=date,
            period="February 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["Hours worked per week"] = metric_entry(
            value=f"{hours_worked} hours/week",
            secondary="Enterprise employees average",
            date=date,
            period="February 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    if service_match:
        snapshot["metrics"]["Service-sector activity"] = metric_entry(
            value=f"{service_match.group(1)}% y/y",
            secondary="Index of Services Production",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    if high_tech_match:
        equipment_growth, high_tech_growth = high_tech_match.groups()
        snapshot["metrics"]["Industrial production by sector"] = metric_entry(
            value=f"Mining 6.1% | Manufacturing 6.6% | Utilities 4.7%",
            secondary=f"Equipment manufacturing {equipment_growth}% | High-tech {high_tech_growth}%",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    summary = "Headline activity release with trade, labor, and price context for the first two months of 2026."
    highlights = []
    if trade_match:
        highlights.append(
            f"Goods trade: RMB {float(total_trade.replace(',', '')) / 1000:.2f} tn, {total_growth}% y/y"
        )
    if unemployment_match:
        highlights.append(f"Urban unemployment: {urban_unemployment}% | 31-city: {unemployment_31}%")
        highlights.append(f"Average hours worked: {hours_worked} per week")

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="nbs-releases",
            release_id="nbs-activity-2026-02",
            title=title,
            date=date,
            url=url,
            summary=summary,
            highlights=highlights,
            tables=[],
        )
    )


def extract_nbs_fai(snapshot: dict[str, Any]) -> None:
    url = "https://www.stats.gov.cn/english/PressRelease/202603/t20260317_1962801.html"
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True))
    date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
    text = article_text(soup)
    tables = read_tables_from_html(html)
    rows = row_lookup(tables[0])

    # Total FAI: "Investment in Fixed Assets (Excluding Rural Households)"
    total_row = (
        row_lookup_contains(rows, "Investment in Fixed Assets")
        or rows.get("Total")
    )
    if total_row:
        snapshot["metrics"]["Total fixed-asset investment"] = metric_entry(
            value=f"{total_row['c1']}% y/y",
            secondary="Jan-Feb growth, excluding rural households",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    private_row = row_lookup_contains(rows, "Non-governmental") or row_lookup_contains(rows, "Private")
    if private_row:
        snapshot["metrics"]["Private fixed-asset investment"] = metric_entry(
            value=f"{private_row['c1']}% y/y",
            secondary="Jan-Feb growth, non-governmental investment",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    state_row = row_lookup_contains(rows, "State-holding") or row_lookup_contains(rows, "State")
    if state_row:
        snapshot["metrics"]["State-owned fixed-asset investment"] = metric_entry(
            value=f"{state_row['c1']}% y/y",
            secondary="Jan-Feb growth",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    if "Manufacturing" in rows:
        snapshot["metrics"]["Manufacturing fixed-asset investment"] = metric_entry(
            value=f"{rows['Manufacturing']['c1']}% y/y",
            secondary="Jan-Feb growth",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    infra_match = re.search(r"investment in infrastructure .*? increased by ([\d.]+)%", text, re.I)
    if infra_match:
        snapshot["metrics"]["Infrastructure fixed-asset investment"] = metric_entry(
            value=f"{infra_match.group(1)}% y/y",
            secondary="Jan-Feb growth",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="nbs-releases",
            release_id="nbs-fai-2026-02",
            title=title,
            date=date,
            url=url,
            summary="Fixed-asset investment release with manufacturing and infrastructure growth rates.",
            highlights=[
                f"Total FAI: {tables[0].iloc[1, 1]}% y/y",
                snapshot["metrics"].get("Manufacturing fixed-asset investment", {}).get("value", "Manufacturing n/a"),
                snapshot["metrics"].get("Infrastructure fixed-asset investment", {}).get("value", "Infrastructure n/a"),
            ],
            tables=[
                dataframe_payload(tables[0], "Fixed-Asset Investment by Sector"),
                dataframe_payload(tables[1], "FAI Month-on-Month Growth"),
            ],
        )
    )


def extract_nbs_industrial_production(snapshot: dict[str, Any]) -> None:
    url = "https://www.stats.gov.cn/english/PressRelease/202603/t20260317_1962800.html"
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True))
    date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
    tables = read_tables_from_html(html)
    rows = row_lookup(tables[0])
    text = article_text(soup)

    headline = rows.get("Value Added of Industrial Enterprises Above the Designated Size")
    if headline:
        snapshot["metrics"]["Industrial production"] = metric_entry(
            value=f"{headline['c2']}% y/y",
            secondary="Value added, Jan-Feb 2026",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    sector_match = re.search(
        r"value added of mining went up by ([\d.]+) percent year on year, manufacturing up by ([\d.]+) percent, and the production and supply of electricity, heat power, gas and water up by ([\d.]+) percent",
        text,
        re.I,
    )
    if sector_match:
        mining_growth, manufacturing_growth, utilities_growth = sector_match.groups()
        snapshot["metrics"]["Industrial production by sector"] = metric_entry(
            value=(
                f"Mining {mining_growth}% | Manufacturing {manufacturing_growth}% | "
                f"Utilities {utilities_growth}%"
            ),
            secondary="Value added y/y",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    output_match = re.search(
        r"including ([\d.]+) million new energy vehicles, (?:down by|up by) ([\d.]+)%", text, re.I
    )
    cement_match = re.search(
        r"that of cement was ([\d.]+) million tons, (up|down) by ([\d.]+)%",
        text,
        re.I,
    )
    nonferrous_match = re.search(
        r"that of ten kinds of non-ferrous metals was ([\d.]+) million tons, (?:up by|down by) ([\d.]+)%",
        text,
        re.I,
    )
    ethylene_match = re.search(
        r"that of ethylene was ([\d.]+) million tons, (?:up by|down by) ([\d.]+)%",
        text,
        re.I,
    )
    steel_match = re.search(
        r"output of rolled steel was ([\d.]+) million tons, (up|down) by ([\d.]+)%",
        text,
        re.I,
    )
    if output_match:
        nevs, nev_change = output_match.groups()
        snapshot["metrics"]["EV output"] = metric_entry(
            value=f"{nevs} mn units",
            secondary=f"{nev_change}% y/y",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )
    if cement_match or steel_match or nonferrous_match or ethylene_match:
        steel_sign = "+" if steel_match and steel_match.group(2).lower() == "up" else "-"
        steel_text = (
            f"Rolled steel {steel_match.group(1)} mn tons, {steel_sign}{steel_match.group(3)}% y/y; "
            if steel_match
            else ""
        )
        cement_sign = "+" if cement_match and cement_match.group(2).lower() == "up" else "-"
        cement_text = (
            f"Cement {cement_match.group(1)} mn tons, {cement_sign}{cement_match.group(3)}% y/y"
            if cement_match
            else "Cement n/a"
        )
        chemical_text = (
            f"Ethylene {ethylene_match.group(1)} mn tons, {ethylene_match.group(2)}% y/y; "
            if ethylene_match
            else ""
        )
        metals_text = (
            f"Non-ferrous metals {nonferrous_match.group(1)} mn tons, {nonferrous_match.group(2)}% y/y"
            if nonferrous_match
            else ""
        )
        snapshot["metrics"]["Steel, cement, glass, and chemicals output"] = metric_entry(
            value=cement_text,
            secondary=f"{steel_text}{chemical_text}{metals_text}".strip(),
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="nbs-releases",
            release_id="nbs-industrial-production-2026-02",
            title=title,
            date=date,
            url=url,
            summary="Industrial production release with headline value-added growth and sector detail.",
            highlights=[
                snapshot["metrics"].get("Industrial production", {}).get("value", "Industrial production n/a"),
                f"High-tech manufacturing: {rows.get('Of which: High Technology Manufacturing', {}).get('c2', 'n/a')}% y/y",
                f"February m/m: {tables[1].iloc[-1, 2]}%",
            ],
            tables=[
                dataframe_payload(tables[0], "Industrial Production Growth"),
                dataframe_payload(tables[1], "Industrial Production Month-on-Month"),
            ],
        )
    )


def extract_nbs_retail(snapshot: dict[str, Any]) -> None:
    url = "https://www.stats.gov.cn/english/PressRelease/202603/t20260317_1962805.html"
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True))
    date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
    tables = read_tables_from_html(html)
    rows = row_lookup(tables[0])

    retail_map = {
        "Retail sales": "Total retail sales of consumer goods",
        "Retail sales ex-autos": "Of which: Retail sales of consumer goods excluding automobiles",
        "Online retail sales": "Of which: Online retail sales of goods",
        "Catering revenue": "Income of the catering industry",
    }
    for metric_name, label in retail_map.items():
        row = rows.get(label)
        if not row:
            continue
        snapshot["metrics"][metric_name] = metric_entry(
            value=from_100m_yuan(row["c1"]),
            secondary=f"{row['c2']}% y/y",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="nbs-releases",
            release_id="nbs-retail-2026-02",
            title=title,
            date=date,
            url=url,
            summary="Retail release with headline consumption, ex-autos, online sales, and category detail.",
            highlights=[
                f"Retail sales: {snapshot['metrics'].get('Retail sales', {}).get('value', 'n/a')}",
                f"Retail ex-autos: {snapshot['metrics'].get('Retail sales ex-autos', {}).get('value', 'n/a')}",
                f"Online retail sales of goods: {snapshot['metrics'].get('Online retail sales', {}).get('value', 'n/a')}",
            ],
            tables=[
                dataframe_payload(tables[0], "Retail Sales by Category"),
                dataframe_payload(tables[1], "Retail Sales Month-on-Month"),
            ],
        )
    )


def extract_nbs_cpi(snapshot: dict[str, Any]) -> None:
    url = latest_nbs_release_url(
        "Consumer Price Index in",
        "https://www.stats.gov.cn/english/PressRelease/202603/t20260310_1962748.html",
    )
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True))
    date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
    tables = read_tables_from_html(html)
    rows = row_lookup(tables[0])
    period_label = period_from_title(title)
    ytd_label = ytd_label_from_table(tables[0])

    cpi_map = {
        "CPI headline": "Consumer Price Index",
        "Food CPI": "Of which: Food",
        "Services CPI": "Services",
        "Core CPI": "Of which: Excluding food and energy",
    }
    for metric_name, label in cpi_map.items():
        row = rows.get(label)
        if not row:
            continue
        snapshot["metrics"][metric_name] = metric_entry(
            value=f"{row['c2']}% y/y",
            secondary=f"{row['c1']}% m/m; {ytd_label} {row['c3']}% y/y",
            date=date,
            period=period_label,
            source_id="nbs-cpi",
            source_title=title,
            source_url=url,
        )

    ppi_url = latest_nbs_release_url(
        "Industrial Producer Price Indexes in",
        "https://www.stats.gov.cn/english/PressRelease/202603/t20260310_1962747.html",
    )
    try:
        ppi_html = fetch(ppi_url).text
        ppi_soup = soup_from_html(ppi_html)
        ppi_tables = read_tables_from_html(ppi_html)
        ppi_rows = row_lookup(ppi_tables[0])
        ppi_row = (
            ppi_rows.get("I. Producer Price Indexes for Industrial Products")
            or ppi_rows.get("Producer Prices for Industrial Products")
            or ppi_rows.get(
            "Industrial Producer Price Index"
            )
        )
        ppi_date = clean_text(ppi_soup.find("meta", attrs={"name": "PubDate"})["content"])
        ppi_title = clean_text(ppi_soup.title.get_text(" ", strip=True))
        ppi_period_label = period_from_title(ppi_title)
        ppi_ytd_label = ytd_label_from_table(ppi_tables[0])
        if ppi_row:
            snapshot["metrics"]["PPI"] = metric_entry(
                value=f"{ppi_row['c2']}% y/y",
                secondary=f"{ppi_row['c1']}% m/m; {ppi_ytd_label} {ppi_row['c3']}% y/y",
                date=ppi_date,
                period=ppi_period_label,
                source_id="nbs-cpi",
                source_title=ppi_title,
                source_url=ppi_url,
            )
    except Exception:
        pass

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="nbs-cpi",
            release_id=f"nbs-cpi-{date.split(' ')[0].replace('/', '-')}",
            title=title,
            date=date,
            url=url,
            summary="CPI release with headline, food, services, and core inflation details.",
            highlights=[
                f"CPI headline: {snapshot['metrics'].get('CPI headline', {}).get('value', 'n/a')}",
                f"Food CPI: {snapshot['metrics'].get('Food CPI', {}).get('value', 'n/a')}",
                f"Services CPI: {snapshot['metrics'].get('Services CPI', {}).get('value', 'n/a')}",
            ],
            tables=[dataframe_payload(tables[0], "Consumer Price Index Breakdown")],
        )
    )


def extract_nbs_pmi(snapshot: dict[str, Any]) -> None:
    url = "https://www.stats.gov.cn/english/PressRelease/202604/t20260401_1962920.html"
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True))
    date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
    tables = read_tables_from_html(html)

    pmi_row = tables[0].iloc[-1]
    rel_row = tables[1].iloc[-1]
    nonmfg_row = tables[2].iloc[-1]

    snapshot["metrics"]["Official manufacturing PMI"] = metric_entry(
        value=f"{pmi_row.iloc[1]}",
        secondary="March 2026",
        date=date,
        period="March 2026",
        source_id="nbs-pmi",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["PMI new orders"] = metric_entry(
        value=f"{pmi_row.iloc[3]}",
        secondary="March 2026",
        date=date,
        period="March 2026",
        source_id="nbs-pmi",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["PMI export orders"] = metric_entry(
        value=f"{rel_row.iloc[1]}",
        secondary="March 2026",
        date=date,
        period="March 2026",
        source_id="nbs-pmi",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["PMI output"] = metric_entry(
        value=f"{pmi_row.iloc[2]}",
        secondary="March 2026",
        date=date,
        period="March 2026",
        source_id="nbs-pmi",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["PMI raw-material inventory"] = metric_entry(
        value=f"{pmi_row.iloc[4]}",
        secondary="March 2026",
        date=date,
        period="March 2026",
        source_id="nbs-pmi",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["PMI finished-goods inventory"] = metric_entry(
        value=f"{rel_row.iloc[6]}",
        secondary="March 2026",
        date=date,
        period="March 2026",
        source_id="nbs-pmi",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["PMI input prices"] = metric_entry(
        value=f"{rel_row.iloc[4]}",
        secondary="March 2026",
        date=date,
        period="March 2026",
        source_id="nbs-pmi",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["PMI output prices"] = metric_entry(
        value=f"{rel_row.iloc[5]}",
        secondary="March 2026",
        date=date,
        period="March 2026",
        source_id="nbs-pmi",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["PMI employment sub-indices"] = metric_entry(
        value=f"Manufacturing {pmi_row.iloc[5]} | Non-manufacturing {nonmfg_row.iloc[5]}",
        secondary="March 2026",
        date=date,
        period="March 2026",
        source_id="nbs-pmi",
        source_title=title,
        source_url=url,
    )

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="nbs-pmi",
            release_id="nbs-pmi-2026-03",
            title=title,
            date=date,
            url=url,
            summary="Full PMI time series tables through March 2026 for manufacturing and non-manufacturing sub-indices.",
            highlights=[
                f"Manufacturing PMI: {snapshot['metrics']['Official manufacturing PMI']['value']}",
                f"New orders: {snapshot['metrics']['PMI new orders']['value']}",
                f"Export orders: {snapshot['metrics']['PMI export orders']['value']}",
            ],
            tables=[
                dataframe_payload(tables[0], "Manufacturing PMI"),
                dataframe_payload(tables[1], "Manufacturing PMI Related Indexes"),
                dataframe_payload(tables[2], "Non-Manufacturing PMI"),
                dataframe_payload(tables[3], "Non-Manufacturing External and Inventory Indexes"),
            ],
        )
    )


def extract_nbs_profits(snapshot: dict[str, Any]) -> None:
    url = "https://www.stats.gov.cn/english/PressRelease/202603/t20260330_1962876.html"
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True))
    date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
    tables = read_tables_from_html(html)

    headline = tables[0].iloc[2]
    efficiency = tables[1].iloc[3]
    sector_rows = row_lookup(tables[2])

    snapshot["metrics"]["Industrial profits"] = metric_entry(
        value=from_100m_yuan(headline.iloc[5]),
        secondary=f"{headline.iloc[6]}% y/y",
        date=date,
        period="Jan-Feb 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Business revenue"] = metric_entry(
        value=from_100m_yuan(headline.iloc[1]),
        secondary=f"{headline.iloc[2]}% y/y",
        date=date,
        period="Jan-Feb 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Operating costs"] = metric_entry(
        value=from_100m_yuan(headline.iloc[3]),
        secondary=f"{headline.iloc[4]}% y/y",
        date=date,
        period="Jan-Feb 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Profit margin / profit rate of revenue"] = metric_entry(
        value=f"{efficiency.iloc[1]}%",
        secondary="Profit rate of business revenue",
        date=date,
        period="Jan-Feb 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Asset-liability ratio"] = metric_entry(
        value=f"{efficiency.iloc[6]}%",
        secondary="End-February 2026",
        date=date,
        period="End-February 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Per-hundred-yuan costs"] = metric_entry(
        value=f"{efficiency.iloc[2]} yuan",
        secondary="Costs per hundred yuan of revenue",
        date=date,
        period="Jan-Feb 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Collection period for receivables"] = metric_entry(
        value=f"{efficiency.iloc[8]} days",
        secondary="End-February 2026",
        date=date,
        period="End-February 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Finished-goods inventory"] = metric_entry(
        value=f"{efficiency.iloc[7]} days",
        secondary="Turnover days of finished-goods inventory",
        date=date,
        period="End-February 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Electronics manufacturing profits"] = metric_entry(
        value=f"{sector_rows.get('Manufacture of computers, communication equipment and other electronic equipment', {}).get('c5', 'n/a')} (100m yuan)",
        secondary=(
            f"{sector_rows.get('Manufacture of computers, communication equipment and other electronic equipment', {}).get('c6', 'n/a')}% y/y"
        ),
        date=date,
        period="Jan-Feb 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Computer and communications equipment profit growth"] = metric_entry(
        value=(
            f"{sector_rows.get('Manufacture of computers, communication equipment and other electronic equipment', {}).get('c6', 'n/a')}% y/y"
        ),
        secondary="Jan-Feb 2026",
        date=date,
        period="Jan-Feb 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Sector profit breakdown"] = metric_entry(
        value="Electronics +200% | Non-ferrous +150% | Autos -30.2%",
        secondary="Headline sector moves in the official release",
        date=date,
        period="Jan-Feb 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    # Ownership breakdown from tables[0]
    ownership_rows = row_lookup(tables[0])
    state_row = row_lookup_contains(ownership_rows, "State-holding")
    private_row = row_lookup_contains(ownership_rows, "Private")
    if state_row:
        try:
            snapshot["metrics"]["State-holding enterprise profit growth"] = metric_entry(
                value=f"{state_row['c6']}% y/y",
                secondary=f"Revenue growth {state_row['c2']}% y/y",
                date=date,
                period="Jan-Feb 2026",
                source_id="nbs-profits",
                source_title=title,
                source_url=url,
            )
        except (KeyError, TypeError):
            pass
    if private_row:
        try:
            snapshot["metrics"]["Private enterprise profit growth"] = metric_entry(
                value=f"{private_row['c6']}% y/y",
                secondary=f"Revenue growth {private_row['c2']}% y/y",
                date=date,
                period="Jan-Feb 2026",
                source_id="nbs-profits",
                source_title=title,
                source_url=url,
            )
        except (KeyError, TypeError):
            pass

    snapshot["metrics"]["Industrial profit margins"] = snapshot["metrics"][
        "Profit margin / profit rate of revenue"
    ]
    snapshot["metrics"]["Industrial enterprise finished-goods inventory"] = metric_entry(
        value=snapshot["metrics"]["Finished-goods inventory"]["value"],
        secondary="Average turnover days of finished-goods inventory",
        date=date,
        period="End-February 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Accounts receivable"] = metric_entry(
        value=snapshot["metrics"]["Collection period for receivables"]["value"],
        secondary="Average collection period for accounts receivable",
        date=date,
        period="End-February 2026",
        source_id="nbs-profits",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Industrial profits by sector"] = snapshot["metrics"]["Sector profit breakdown"]

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="nbs-profits",
            release_id="nbs-profits-2026-02",
            title=title,
            date=date,
            url=url,
            summary="Industrial profits, margins, leverage, and sector cash-flow table set.",
            highlights=[
                f"Industrial profits: {snapshot['metrics']['Industrial profits']['value']}",
                f"Profit margin: {snapshot['metrics']['Profit margin / profit rate of revenue']['value']}",
                f"Collection period: {snapshot['metrics']['Collection period for receivables']['value']}",
            ],
            tables=[
                dataframe_payload(tables[0], "Industrial Profits, Revenue, and Costs"),
                dataframe_payload(tables[1], "Industrial Efficiency Indicators"),
                dataframe_payload(tables[2], "Industrial Profits by Sector"),
            ],
        )
    )


def extract_nbs_energy(snapshot: dict[str, Any]) -> None:
    url = "https://www.stats.gov.cn/english/PressRelease/202603/t20260317_1962806.html"
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True))
    date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
    text = article_text(soup)

    electricity_match = re.search(
        r"electricity generation.*?was ([\d.,]+) billion (?:kWh|kilowatt-hours), (?:up by|a year-on-year increase of) ([\d.]+)%",
        text,
        re.I,
    )
    thermal_match = re.search(
        r"thermal power generation by industrial enterprises above the designated size increased by ([\d.]+)% year on year",
        text,
        re.I,
    )

    if electricity_match:
        output, growth = electricity_match.groups()
        snapshot["metrics"]["Electricity generation"] = metric_entry(
            value=f"{float(output.replace(',', '')):.1f} bn kWh",
            secondary=f"{growth}% y/y",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    if thermal_match:
        snapshot["metrics"]["Thermal power output"] = metric_entry(
            value=f"{thermal_match.group(1)}% y/y",
            secondary="Jan-Feb 2026",
            date=date,
            period="Jan-Feb 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="nbs-releases",
            release_id="nbs-energy-2026-02",
            title=title,
            date=date,
            url=url,
            summary="Energy production release with coal, oil, gas, and electricity generation.",
            highlights=[
                snapshot["metrics"].get("Electricity generation", {}).get("value", "Electricity n/a"),
                snapshot["metrics"].get("Thermal power output", {}).get("value", "Thermal power n/a"),
                "Raw coal production: 760 mn tons, -0.3% y/y",
            ],
            tables=[],
        )
    )


def extract_nbs_annual(snapshot: dict[str, Any]) -> None:
    url = "https://www.stats.gov.cn/english/PressRelease/202602/t20260228_1962661.html"
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True))
    date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
    text = article_text(soup)
    tables = read_tables_from_html(html)
    population = row_lookup(tables[0])
    output_table = row_lookup(tables[2])

    birth_match = re.search(
        r"There were ([\d.]+) million births in 2025 with a crude birth rate of ([\d.]+) per thousand; and there were ([\d.]+) million deaths.*?The natural growth rate was (-?[\d.]+) per thousand",
        text,
        re.I,
    )
    migrant_match = first_match(
        text,
        [
            r"total number of migrant workers[^.]*?was ([\d.]+) million, up by ([\d.]+) percent",
            r"migrant workers[^.]*?was ([\d.]+) million, up by ([\d.]+) percent",
        ],
    )

    snapshot["metrics"]["Total population"] = metric_entry(
        value=f"{float(population['National Total']['c1']) / 100000:.4f} bn",
        secondary="Year-end 2025",
        date=date,
        period="End-2025",
        source_id="nbs-communique",
        source_title=title,
        source_url=url,
    )
    urban_row = row_lookup_contains(population, "Of which: Urban")
    working_age_row = row_lookup_contains(population, "Aged 16-59")
    age_0_15_row = row_lookup_contains(population, "Aged 0-15")
    age_60_row = row_lookup_contains(population, "Aged 60 and above")
    age_65_row = row_lookup_contains(population, "Aged 65 and above")

    snapshot["metrics"]["Urbanization rate"] = metric_entry(
        value=f"{urban_row['c2']}%",
        secondary="Year-end 2025",
        date=date,
        period="End-2025",
        source_id="nbs-communique",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Urban permanent residents"] = metric_entry(
        value=f"{float(urban_row['c1']) / 10000:.3f} bn",
        secondary=f"{urban_row['c2']}% of total population",
        date=date,
        period="End-2025",
        source_id="nbs-communique",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Working-age population share"] = metric_entry(
        value=f"{working_age_row['c2']}%",
        secondary="Year-end 2025",
        date=date,
        period="End-2025",
        source_id="nbs-communique",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Age structure"] = metric_entry(
        value=(
            f"0-15: {age_0_15_row['c2']}% | "
            f"60+: {age_60_row['c2']}% | "
            f"65+: {age_65_row['c2']}%"
        ),
        secondary="Year-end 2025",
        date=date,
        period="End-2025",
        source_id="nbs-communique",
        source_title=title,
        source_url=url,
    )

    if birth_match:
        births, birth_rate, deaths, natural_growth = birth_match.groups()
        snapshot["metrics"]["Births"] = metric_entry(
            value=f"{births} mn",
            secondary=f"Crude birth rate {birth_rate} per thousand",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["Deaths"] = metric_entry(
            value=f"{deaths} mn",
            secondary="2025",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["Natural population growth"] = metric_entry(
            value=f"{natural_growth} per thousand",
            secondary="2025",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )

    if migrant_match:
        migrant_workers, growth = migrant_match.groups()
        snapshot["metrics"]["Migrant worker population"] = metric_entry(
            value=f"{migrant_workers} mn",
            secondary=f"{growth}% y/y",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["Migrant worker totals"] = snapshot["metrics"]["Migrant worker population"]

    snapshot["metrics"]["Integrated-circuit output"] = metric_entry(
        value=f"{output_table['Integrated circuits']['c2']} (100m pieces)",
        secondary=f"{output_table['Integrated circuits']['c3']}% y/y",
        date=date,
        period="2025",
        source_id="nbs-communique",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Solar-cell output"] = metric_entry(
        value=f"{output_table['Solar cells (photovoltaic cells)']['c2']} (10k kW)",
        secondary=f"{output_table['Solar cells (photovoltaic cells)']['c3']}% y/y",
        date=date,
        period="2025",
        source_id="nbs-communique",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Mobile telephones"] = metric_entry(
        value=f"{output_table['Mobile telephones']['c2']} (10k units)",
        secondary=f"{output_table['Mobile telephones']['c3']}% y/y",
        date=date,
        period="2025",
        source_id="nbs-communique",
        source_title=title,
        source_url=url,
    )
    nev_match = re.search(
        r"output of new energy vehicles reached ([\d.]+) million, up by ([\d.]+) percent",
        text,
        re.I,
    )
    if nev_match:
        nev_output, nev_growth = nev_match.groups()
        snapshot["metrics"]["EV output"] = metric_entry(
            value=f"{nev_output} mn units",
            secondary=f"+{nev_growth}% y/y in 2025",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )

    rail_freight_row = find_row_in_tables(tables, "Railways", unit_contains="100 million tons")
    if rail_freight_row:
        snapshot["metrics"]["Rail freight"] = metric_entry(
            value=f"{rail_freight_row['value']} {rail_freight_row['unit']}",
            secondary=f"{rail_freight_row['change']}% y/y",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )
    freight_flow_row = find_row_in_tables(
        tables,
        "Freight flows",
        unit_contains="100 million ton-kilometers",
    )
    if freight_flow_row:
        snapshot["metrics"]["Freight traffic / ton-kilometers"] = metric_entry(
            value=f"{freight_flow_row['value']} {freight_flow_row['unit']}",
            secondary=f"{freight_flow_row['change']}% y/y",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )

    high_tech_match = re.search(
        r"value added of high-tech manufacturing .*? increased by ([\d.]+) percent.*?profits made by high-tech manufacturing enterprises grew by ([\d.]+) percent",
        text,
        re.I,
    )
    high_tech_investment_match = re.search(
        r"investment in high technology industr(?:y|ies).*? increased by ([\d.]+) percent.*?technology transformation of manufacturing.*? grew by ([\d.]+) percent",
        text,
        re.I,
    )
    if high_tech_match:
        va_growth, profit_growth = high_tech_match.groups()
        snapshot["metrics"]["High-tech manufacturing investment"] = metric_entry(
            value=f"Value added +{va_growth}% y/y",
            secondary=f"Profit growth +{profit_growth}% y/y in 2025",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )
    if high_tech_investment_match:
        high_tech_growth, tech_transform_growth = high_tech_investment_match.groups()
        snapshot["metrics"]["High-tech industry investment"] = metric_entry(
            value=f"{high_tech_growth}% y/y",
            secondary="Annual high-technology industry investment growth",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["Technology-transformation investment"] = metric_entry(
            value=f"{tech_transform_growth}% y/y",
            secondary="Annual manufacturing technology-transformation investment growth",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )

    # GDP expenditure decomposition
    consumption_contrib = first_match(
        text,
        [
            r"final consumption expenditure contributed ([\d.]+) percentage points? to .*?GDP growth",
            r"final consumption expenditure.*?contributed ([\d.]+) percentage points?",
        ],
    )
    investment_contrib = first_match(
        text,
        [
            r"gross capital formation contributed ([\d.]+) percentage points? to .*?GDP growth",
            r"gross capital formation.*?contributed ([\d.]+) percentage points?",
        ],
    )
    net_exports_contrib = first_match(
        text,
        [
            r"net exports? of goods and services contributed (-?[\d.]+) percentage points?",
        ],
    )
    if consumption_contrib:
        snapshot["metrics"]["Consumption contribution to GDP growth"] = metric_entry(
            value=f"+{consumption_contrib.group(1)} pp",
            secondary="Final consumption expenditure contribution to annual GDP growth",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )
    if investment_contrib:
        snapshot["metrics"]["Investment contribution to GDP growth"] = metric_entry(
            value=f"+{investment_contrib.group(1)} pp",
            secondary="Gross capital formation contribution to annual GDP growth",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )
    if net_exports_contrib:
        val = net_exports_contrib.group(1)
        snapshot["metrics"]["Net exports contribution to GDP growth"] = metric_entry(
            value=f"{float(val):+.1f} pp",
            secondary="Net exports of goods and services contribution to annual GDP growth",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )

    # Services share of GDP and value-added growth
    tertiary_share = first_match(
        text,
        [
            r"value added of the tertiary industry.*?(?:an increase|grew|growth) (?:of |by )?([\d.]+) percent.*?accounting for ([\d.]+) percent of GDP",
            r"tertiary industry.*?(?:increased|grew) (?:by )?([\d.]+) percent.*?accounting for ([\d.]+) percent",
        ],
    )
    if tertiary_share:
        services_growth = tertiary_share.group(1)
        services_share = tertiary_share.group(2)
        snapshot["metrics"]["Services share of GDP"] = metric_entry(
            value=f"{services_share}%",
            secondary=f"Tertiary industry value added grew {services_growth}% y/y",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["Services value-added growth"] = metric_entry(
            value=f"{services_growth}% y/y",
            secondary=f"Services share {services_share}% of GDP",
            date=date,
            period="2025",
            source_id="nbs-communique",
            source_title=title,
            source_url=url,
        )

    # Household savings rate
    income_level_match = first_match(
        text,
        [
            r"per capita disposable income (?:of residents )?nationwide was ([\d,]+) yuan",
            r"per capita disposable income.*?was ([\d,]+) yuan",
        ],
    )
    expenditure_level_match = first_match(
        text,
        [
            r"per capita consumer expenditure (?:of residents )?(?:nationwide )?was ([\d,]+) yuan",
            r"per capita consumption expenditure.*?was ([\d,]+) yuan",
        ],
    )
    if income_level_match and expenditure_level_match:
        income_yuan = float(income_level_match.group(1).replace(",", ""))
        expenditure_yuan = float(expenditure_level_match.group(1).replace(",", ""))
        if income_yuan > 0:
            savings_rate = ((income_yuan - expenditure_yuan) / income_yuan) * 100
            snapshot["metrics"]["Household savings rate"] = metric_entry(
                value=f"{savings_rate:.1f}%",
                secondary=f"(RMB {income_yuan:,.0f} income \u2212 RMB {expenditure_yuan:,.0f} expenditure) / income",
                date=date,
                period="2025",
                source_id="nbs-communique",
                source_title=f"Computed: Household savings rate from {title}",
                source_url=url,
            )

    # Labor productivity (GDP per employed person)
    employment_match = first_match(
        text,
        [
            r"(?:total number of )?(?:persons employed|employed persons) (?:in urban areas |nationwide )?(?:at year-end |at the end of \d{4} )?(?:totaled|was|reached|stood at) ([\d.]+) million",
            r"(?:total employed persons|persons employed).*?was ([\d.]+) million",
        ],
    )
    gdp_level_match = re.search(
        r"gross domestic product.*?was ([\d,.]+) billion yuan",
        text,
        re.I,
    )
    if gdp_level_match and employment_match:
        try:
            gdp_bn = float(gdp_level_match.group(1).replace(",", ""))
            employment_mn = float(employment_match.group(1))
            if employment_mn > 0:
                productivity = gdp_bn * 1000 / employment_mn  # million yuan per person
                snapshot["metrics"]["Labor productivity (GDP per employed person)"] = metric_entry(
                    value=f"RMB {productivity:,.0f} per person",
                    secondary=f"GDP RMB {gdp_bn:,.0f} bn / {employment_mn:.0f} mn employed",
                    date=date,
                    period="2025",
                    source_id="nbs-communique",
                    source_title=f"Computed: GDP per employed person from {title}",
                    source_url=url,
                )
        except (ValueError, ZeroDivisionError):
            pass

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="nbs-communique",
            release_id="nbs-annual-2025",
            title=title,
            date=date,
            url=url,
            summary="Annual structural snapshot for demographics, urbanization, industrial output, and strategic sectors.",
            highlights=[
                f"Population: {snapshot['metrics']['Total population']['value']}",
                f"Urbanization: {snapshot['metrics']['Urbanization rate']['value']}",
                f"Migrant workers: {snapshot['metrics'].get('Migrant worker population', {}).get('value', 'n/a')}",
            ],
            tables=[
                dataframe_payload(tables[0], "Population and Composition"),
                dataframe_payload(tables[2], "Selected Industrial Output"),
                dataframe_payload(tables[6], "Fixed-Asset Investment by Sector in 2025"),
            ],
        )
    )


def extract_nbs_chinese_releases(snapshot: dict[str, Any]) -> None:
    property_url = "https://www.stats.gov.cn/sj/zxfb/202603/t20260316_1962785.html"
    capacity_url = "https://www.stats.gov.cn/sj/zxfb/202601/t20260119_1962320.html"
    wage_url = "https://www.stats.gov.cn/zwfwck/sjfb/202505/t20250516_1959826.html"
    trade_qa_url = "https://www.stats.gov.cn/sj/sjjd/202603/t20260316_1962795.html"

    property_html = requests.get(property_url, timeout=(20, 90), headers=SESSION.headers, verify=False)
    property_html.encoding = "utf-8"
    property_text = article_text(soup_from_html(property_html.text))

    capacity_html = requests.get(capacity_url, timeout=(20, 90), headers=SESSION.headers, verify=False)
    capacity_html.encoding = "utf-8"
    capacity_text = article_text(soup_from_html(capacity_html.text))

    wage_html = requests.get(wage_url, timeout=(20, 90), headers=SESSION.headers, verify=False)
    wage_html.encoding = "utf-8"
    wage_text = article_text(soup_from_html(wage_html.text))

    trade_html = requests.get(trade_qa_url, timeout=(20, 90), headers=SESSION.headers, verify=False)
    trade_html.encoding = "utf-8"
    trade_text = article_text(soup_from_html(trade_html.text))

    quarter_match = re.search(r"2025\s*年四季度，全国(?:规模以上)?工业产能利用率为\s*([\d.]+)%", capacity_text)
    annual_match = re.search(r"2025\s*年全国(?:规模以上)?工业产能利用率为\s*([\d.]+)%", capacity_text)
    manufacturing_match = re.search(r"制造业产能利用率为\s*([\d.]+)%", capacity_text)
    if quarter_match and annual_match:
        quarter = quarter_match.group(1)
        annual = annual_match.group(1)
        manufacturing = manufacturing_match.group(1) if manufacturing_match else None
        secondary_bits = [f"Q4 {quarter}%"]
        if manufacturing:
            secondary_bits.append(f"Manufacturing {manufacturing}%")
        snapshot["metrics"]["Capacity utilization"] = metric_entry(
            value=f"{annual}%",
            secondary="; ".join(secondary_bits),
            date="2026-01-19",
            period="2025",
            source_id="nbs-releases",
            source_title="2025年四季度全国规模以上工业产能利用率为74.9% - 国家统计局",
            source_url=capacity_url,
        )
        add_history_point(
            snapshot,
            metric_name="Capacity utilization",
            value=f"{annual}%",
            numeric=float(annual),
            date="2026-01-19",
            period="2025",
            source_id="nbs-releases",
            source_title="2025年四季度全国规模以上工业产能利用率为74.9% - 国家统计局",
            source_url=capacity_url,
            secondary="; ".join(secondary_bits),
        )

    wage_non_private = re.search(
        r"全国城镇非私营单位就业人员年平均工资(?:为)?\s*([\d]+)\s*元[^。]*?名义增长(?:\s*\[\d+\])?\s*([\d.]+)%",
        wage_text,
        re.I,
    )
    wage_private = re.search(
        r"全国城镇私营单位就业人员年平均工资(?:为)?\s*([\d]+)\s*元[^。]*?名义增长(?:\s*\[\d+\])?\s*([\d.]+)%",
        wage_text,
        re.I,
    )
    wage_enterprise = re.search(
        r"规模以上企业就业人员年平均工资(?:为)?\s*([\d]+)\s*元[^。]*?名义增长(?:\s*\[\d+\])?\s*([\d.]+)%",
        wage_text,
        re.I,
    )
    if wage_non_private and wage_private and wage_enterprise:
        _, non_private_growth = wage_non_private.groups()
        _, private_growth = wage_private.groups()
        enterprise_level, enterprise_growth = wage_enterprise.groups()
        snapshot["metrics"]["Average wage growth"] = metric_entry(
            value=f"Non-private +{float(non_private_growth):.1f}%",
            secondary=(
                f"Private +{float(private_growth):.1f}%; "
                f"large enterprises +{float(enterprise_growth):.1f}% (RMB {int(enterprise_level):,})"
            ),
            date="2025-05-16",
            period="2024",
            source_id="nbs-releases",
            source_title="2024年城镇单位就业人员年平均工资情况",
            source_url=wage_url,
        )
        add_history_point(
            snapshot,
            metric_name="Average wage growth",
            value=f"{float(non_private_growth):.1f}%",
            numeric=float(non_private_growth),
            date="2025-05-16",
            period="2024",
            source_id="nbs-releases",
            source_title="2024年城镇单位就业人员年平均工资情况",
            source_url=wage_url,
            secondary=f"Private +{float(private_growth):.1f}%",
        )

    if "土地购置费" in property_text and "Land purchase area by developers" not in snapshot["metrics"]:
        legacy_title, legacy_description = ceic_page_payload(
            "https://www.ceicdata.com/en/china/land-purchase-and-development/cn-land-area-purchased-ytd"
        )
        legacy_parsed = parse_ceic_description(legacy_description)
        if legacy_parsed:
            snapshot["metrics"]["Land purchase area by developers"] = metric_entry(
                value=format_ceic_value(legacy_parsed["latest"], legacy_parsed["latest_unit"]),
                secondary=(
                    f"Latest accessible CEIC/NBS point {legacy_parsed['latest_period']}; "
                    f"{legacy_parsed['previous_period']}: "
                    f"{format_ceic_value(legacy_parsed['previous'], legacy_parsed['previous_unit'])}"
                ),
                date=english_month_year_to_iso(legacy_parsed["latest_period"]),
                period=legacy_parsed["latest_period"],
                source_id="nbs-releases",
                source_title=legacy_title,
                source_url="https://www.ceicdata.com/en/china/land-purchase-and-development/cn-land-area-purchased-ytd",
            )
            add_history_point(
                snapshot,
                metric_name="Land purchase area by developers",
                value=format_ceic_value(legacy_parsed["latest"], legacy_parsed["latest_unit"]),
                numeric=parse_float(legacy_parsed["latest"]),
                date=english_month_year_to_iso(legacy_parsed["latest_period"]),
                period=legacy_parsed["latest_period"],
                source_id="nbs-releases",
                source_title=legacy_title,
                source_url="https://www.ceicdata.com/en/china/land-purchase-and-development/cn-land-area-purchased-ytd",
                secondary="Latest accessible series point from CEIC, reported by NBS",
            )

    trade_match = re.search(r"东盟、欧盟、共建[“\"]?一带一路[”\"]?国家等进出口增速都保持在\s*20%\s*左右", trade_text)
    if trade_match:
        snapshot["metrics"]["Exports by destination"] = metric_entry(
            value="ASEAN / EU / Belt & Road around +20%",
            secondary="Official NBS Jan-Feb 2026 Q&A said major destination-group trade growth stayed around 20%",
            date="2026-03-16",
            period="Jan-Feb 2026",
            source_id="gacc-stats",
            source_title="国家统计局新闻发言人就2026年1—2月份国民经济运行情况答记者问",
            source_url=trade_qa_url,
        )

    snapshot["sourceSnapshots"].extend(
        [
            source_snapshot(
                source_id="nbs-releases",
                release_id="nbs-capacity-2025-q4-cn",
                title="2025年四季度全国规模以上工业产能利用率为74.9% - 国家统计局",
                date="2026-01-19",
                url=capacity_url,
                summary="Chinese NBS quarterly capacity-utilization release used to fill the utilization gap on the dashboard.",
                highlights=[
                    snapshot["metrics"].get("Capacity utilization", {}).get("value", "n/a"),
                    snapshot["metrics"].get("Capacity utilization", {}).get("secondary", ""),
                ],
                tables=[],
            ),
            source_snapshot(
                source_id="nbs-releases",
                release_id="nbs-average-wages-2024-cn",
                title="2024年城镇单位就业人员年平均工资情况",
                date="2025-05-16",
                url=wage_url,
                summary="Chinese NBS wage release covering non-private, private, and large-enterprise wage growth.",
                highlights=[
                    snapshot["metrics"].get("Average wage growth", {}).get("value", "n/a"),
                    snapshot["metrics"].get("Average wage growth", {}).get("secondary", ""),
                ],
                tables=[],
            ),
            source_snapshot(
                source_id="gacc-stats",
                release_id="nbs-trade-qa-2026-02-cn",
                title="国家统计局新闻发言人就2026年1—2月份国民经济运行情况答记者问",
                date="2026-03-16",
                url=trade_qa_url,
                summary="NBS Q&A page summarizing the breadth of destination-market trade growth.",
                highlights=[
                    snapshot["metrics"].get("Exports by destination", {}).get("value", "n/a"),
                    snapshot["metrics"].get("Exports by destination", {}).get("secondary", ""),
                ],
                tables=[],
            ),
        ]
    )


def extract_pboc_financial(snapshot: dict[str, Any]) -> None:
    url = "https://www.pbc.gov.cn/en/3688247/3688978/3709137/2026031614261747241/index.html"
    html = fetch(url).text
    soup = soup_from_html(html)
    text = article_text(soup)
    title = clean_text(
        soup.find("meta", attrs={"name": "ArticleTitle"})["content"]
        if soup.find("meta", attrs={"name": "ArticleTitle"})
        else "Financial Statistics Report (February 2026)"
    )
    date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])

    afre_stock = re.search(
        r"AFRE\) reached RMB([\d.]+) trillion at end-February 2026, increasing ([\d.]+) percent",
        text,
        re.I,
    )
    afre_flow = re.search(
        r"AFRE\) \(flow\) was RMB([\d.]+) trillion in the first two months of 2026, up RMB([\d.]+) billion",
        text,
        re.I,
    )
    flow_breakdown = re.search(
        (
            r"RMB loans to the real economy registered an increase of RMB([\d.]+) trillion.*?"
            r"entrusted loans registered a decrease of RMB([\d.]+) billion.*?"
            r"trust loans recorded an increase of RMB([\d.]+) billion.*?"
            r"undiscounted bankers' acceptances recorded an increase of RMB([\d.]+) billion.*?"
            r"net financing of government bonds was RMB([\d.]+) trillion"
        ),
        text,
        re.I,
    )
    m2_match = re.search(
        r"M2\) stood at RMB([\d.]+) trillion, rising by ([\d.]+) percent.*?M1\), at RMB([\d.]+) trillion, grew by ([\d.]+) percent",
        text,
        re.I,
    )
    deposits_match = re.search(
        r"household deposits.*? rose by RMB([\d.]+) trillion",
        text,
        re.I,
    )
    loans_match = re.search(
        (
            r"new RMB loans totaled RMB([\d.]+) trillion.*?"
            r"household loans decreased by RMB([\d.]+) billion.*?"
            r"medium- and long-term \(MLT\) loans increasing by RMB([\d.]+) billion;.*?"
            r"loans to enterprises and public institutions grew by RMB([\d.]+) trillion.*?"
            r"medium- and long-term \(MLT\) loans, while bill financing decreased by RMB([\d.]+) billion"
        ),
        text,
        re.I,
    )
    enterprise_match = re.search(
        r"increase of RMB([\d.]+) trillion in short-term loans and RMB([\d.]+) trillion in medium- and long-term \(MLT\) loans",
        text,
        re.I,
    )

    if afre_stock:
        level, growth = afre_stock.groups()
        snapshot["metrics"]["TSF stock growth"] = metric_entry(
            value=f"{growth}% y/y",
            secondary=f"Outstanding AFRE {format_trillion_yuan(level)}",
            date=date,
            period="End-February 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )

    if afre_flow:
        flow, yoy_delta = afre_flow.groups()
        snapshot["metrics"]["TSF flow"] = metric_entry(
            value=format_trillion_yuan(flow),
            secondary=f"Up RMB {float(yoy_delta):.1f} bn vs Jan-Feb 2025",
            date=date,
            period="Jan-Feb 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )

    if flow_breakdown:
        _, entrusted, trust, acceptances, government_bonds = flow_breakdown.groups()
        snapshot["metrics"]["Entrusted loans"] = metric_entry(
            value=f"-RMB {float(entrusted):.1f} bn",
            secondary="AFRE flow contribution",
            date=date,
            period="Jan-Feb 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["Trust loans"] = metric_entry(
            value=f"+RMB {float(trust):.1f} bn",
            secondary="AFRE flow contribution",
            date=date,
            period="Jan-Feb 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["Bankers' acceptances"] = metric_entry(
            value=f"+RMB {float(acceptances):.1f} bn",
            secondary="AFRE flow contribution",
            date=date,
            period="Jan-Feb 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["Government bond financing within TSF"] = metric_entry(
            value=format_trillion_yuan(government_bonds),
            secondary="Net financing in AFRE flow",
            date=date,
            period="Jan-Feb 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )

    if m2_match:
        m2_level, m2_growth, m1_level, m1_growth = m2_match.groups()
        snapshot["metrics"]["M2 growth"] = metric_entry(
            value=f"{m2_growth}% y/y",
            secondary=f"Outstanding M2 {format_trillion_yuan(m2_level)}",
            date=date,
            period="End-February 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["M1 growth"] = metric_entry(
            value=f"{m1_growth}% y/y",
            secondary=f"Outstanding M1 {format_trillion_yuan(m1_level)}",
            date=date,
            period="End-February 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )

    if deposits_match:
        snapshot["metrics"]["Household deposits"] = metric_entry(
            value=format_trillion_yuan(deposits_match.group(1)),
            secondary="Increase in Jan-Feb 2026",
            date=date,
            period="Jan-Feb 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )

    # Household deposit growth — try to extract y/y deposit growth rate from the text
    deposit_growth_match = re.search(
        r"household deposits.*?(?:rose|increased|grew) by.*?(?:up|rising|increasing) ([\d.]+) percent",
        text,
        re.I,
    )
    if not deposit_growth_match:
        # Alternative: look for deposit growth expressed differently
        deposit_growth_match = re.search(
            r"deposits (?:of|by) households.*?(?:rose|increased|grew).*?([\d.]+) percent",
            text,
            re.I,
        )
    if deposit_growth_match:
        snapshot["metrics"]["Household deposit growth"] = metric_entry(
            value=f"{deposit_growth_match.group(1)}% y/y",
            secondary="Household deposit y/y growth",
            date=date,
            period="End-February 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )
    elif deposits_match and m2_match:
        # Fallback: report the flow as a proxy with a note
        snapshot["metrics"]["Household deposit growth"] = metric_entry(
            value=f"+{format_trillion_yuan(deposits_match.group(1))} flow",
            secondary="Net increase in household deposits; y/y growth rate not explicitly stated in release",
            date=date,
            period="Jan-Feb 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )

    if loans_match and enterprise_match:
        total_loans, household_loans, household_mlt, enterprise_loans, bill_decline = loans_match.groups()
        enterprise_short, enterprise_mlt = enterprise_match.groups()
        snapshot["metrics"]["New RMB loans"] = metric_entry(
            value=format_trillion_yuan(total_loans),
            secondary="Jan-Feb 2026",
            date=date,
            period="Jan-Feb 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["Household loans"] = metric_entry(
            value=f"-RMB {float(household_loans):.1f} bn",
            secondary="Jan-Feb 2026",
            date=date,
            period="Jan-Feb 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["Household medium/long-term loans"] = metric_entry(
            value=f"+RMB {float(household_mlt):.1f} bn",
            secondary="Jan-Feb 2026",
            date=date,
            period="Jan-Feb 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )
        snapshot["metrics"]["Household medium/long-term loans (mortgage proxy)"] = snapshot["metrics"][
            "Household medium/long-term loans"
        ]
        snapshot["metrics"]["Corporate medium/long-term loans"] = metric_entry(
            value=format_trillion_yuan(enterprise_mlt),
            secondary=f"Enterprises and public institutions; short-term +RMB {float(enterprise_short):.2f} tn",
            date=date,
            period="Jan-Feb 2026",
            source_id="pboc-home",
            source_title=title,
            source_url=url,
        )

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="pboc-home",
            release_id="pboc-financial-statistics-2026-02",
            title=title,
            date=date,
            url=url,
            summary="PBOC financial statistics report covering AFRE, loans, deposits, and money supply.",
            highlights=[
                f"AFRE flow: {snapshot['metrics'].get('TSF flow', {}).get('value', 'n/a')}",
                f"New RMB loans: {snapshot['metrics'].get('New RMB loans', {}).get('value', 'n/a')}",
                f"M2 growth: {snapshot['metrics'].get('M2 growth', {}).get('value', 'n/a')}",
            ],
            tables=[],
        )
    )


def extract_pboc_policy(snapshot: dict[str, Any]) -> None:
    lpr_url = "https://www.pbc.gov.cn/en/3688229/3688335/3730276/3883798/2026032014293224083/index.html"
    lpr_html = fetch(lpr_url).text
    lpr_soup = soup_from_html(lpr_html)
    lpr_title = clean_text(lpr_soup.find("meta", attrs={"name": "ArticleTitle"})["content"])
    lpr_date = clean_text(lpr_soup.find("meta", attrs={"name": "PubDate"})["content"])
    lpr_text = article_text(lpr_soup)
    lpr_match = re.search(r"one-year LPR is ([\d.]+)% and the over-five-year LPR is ([\d.]+)%", lpr_text)
    if lpr_match:
        one_year, five_year = lpr_match.groups()
        snapshot["metrics"]["1-year LPR"] = metric_entry(
            value=f"{one_year}%",
            secondary="Effective until the next release",
            date=lpr_date,
            period="March 20, 2026",
            source_id="pboc-home",
            source_title=lpr_title,
            source_url=lpr_url,
        )
        snapshot["metrics"]["5-year LPR"] = metric_entry(
            value=f"{five_year}%",
            secondary="Effective until the next release",
            date=lpr_date,
            period="March 20, 2026",
            source_id="pboc-home",
            source_title=lpr_title,
            source_url=lpr_url,
        )

    mlf_url = "https://www.pbc.gov.cn/en/3688229/3688335/3730273/3730282/2026022713554623890/index.html"
    mlf_html = fetch(mlf_url).text
    mlf_soup = soup_from_html(mlf_html)
    mlf_title = clean_text(mlf_soup.find("meta", attrs={"name": "ArticleTitle"})["content"])
    mlf_date = clean_text(mlf_soup.find("meta", attrs={"name": "PubDate"})["content"])
    mlf_text = article_text(mlf_soup)
    mlf_match = re.search(
        r"amount of RMB([\d.]+) billion with a term of one year",
        mlf_text,
        re.I,
    )
    if mlf_match:
        snapshot["metrics"]["MLF rate"] = metric_entry(
            value="Variable-rate tender regime",
            secondary=f"Latest tender amount {format_billion_yuan(mlf_match.group(1))}; one-year term",
            date=mlf_date,
            period="February 24, 2026",
            source_id="pboc-home",
            source_title=mlf_title,
            source_url=mlf_url,
        )

    omo_url = "https://www.pbc.gov.cn/en/3688110/3688181/2026041313415087263/index.html"
    omo_html = fetch(omo_url).text
    omo_tables = read_tables_from_html(omo_html)
    omo_table = omo_tables[0]
    omo_title = "Announcement on Open Market Operations No.69 [2026]"
    omo_date = "2026-04-13"
    snapshot["metrics"]["7-day reverse repo rate"] = metric_entry(
        value=omo_table.iloc[1, 1],
        secondary=f"Bidding volume {omo_table.iloc[1, 2]}",
        date=omo_date,
        period="April 13, 2026",
        source_id="pboc-home",
        source_title=omo_title,
        source_url=omo_url,
    )
    snapshot["metrics"]["PBOC liquidity operations"] = metric_entry(
        value=f"{omo_table.iloc[1, 0]} reverse repo | {omo_table.iloc[1, 2]}",
        secondary=f"Winning volume {omo_table.iloc[1, 3]}",
        date=omo_date,
        period="April 13, 2026",
        source_id="pboc-home",
        source_title=omo_title,
        source_url=omo_url,
    )

    outright_url = "https://www.pbc.gov.cn/en/3688110/3688181/2026041014090488842/index.html"
    outright_html = fetch(outright_url).text
    outright_soup = soup_from_html(outright_html)
    outright_text = article_text(outright_soup)
    outright_title = clean_text(
        outright_soup.find("meta", attrs={"name": "ArticleTitle"})["content"]
        if outright_soup.find("meta", attrs={"name": "ArticleTitle"})
        else "Announcement on Open Market Outright Reverse Repo Tenders No.7 [2026]"
    )
    outright_date = clean_text(outright_soup.find("meta", attrs={"name": "PubDate"})["content"])
    outright_match = re.search(
        r"amount of RMB([\d.]+) billion.*?maturity of the operation will be ([\d]+ months?)",
        outright_text,
        re.I,
    )

    rrr_url = "https://www.pbc.gov.cn/en/3688229/3688335/3730270/2025112115010879277/index.html"
    rrr_html = fetch(rrr_url).text
    rrr_soup = soup_from_html(rrr_html)
    rrr_title = clean_text(rrr_soup.find("meta", attrs={"name": "ArticleTitle"})["content"])
    rrr_date = clean_text(rrr_soup.find("meta", attrs={"name": "PubDate"})["content"])
    rrr_desc = rrr_soup.find("meta", attrs={"name": "Description"})["content"]
    rrr_match = re.search(
        r"cut the required reserve ratio \(RRR\) .*? by ([\d.]+) percentage points.*?effective from ([A-Za-z]+ \d+)",
        rrr_desc,
        re.I,
    )
    if rrr_match:
        change, effective = rrr_match.groups()
        snapshot["metrics"]["RRR changes"] = metric_entry(
            value=f"-{change} pp",
            secondary=f"Effective {effective}; latest accessible English RRR announcement",
            date=rrr_date,
            period="May 2025 announcement",
            source_id="pboc-home",
            source_title=rrr_title,
            source_url=rrr_url,
        )

    snapshot["sourceSnapshots"].extend(
        [
            source_snapshot(
                source_id="pboc-home",
                release_id="pboc-lpr-2026-03-20",
                title=lpr_title,
                date=lpr_date,
                url=lpr_url,
                summary="Latest accessible LPR release on the PBOC English site.",
                highlights=[
                    f"1-year LPR: {snapshot['metrics'].get('1-year LPR', {}).get('value', 'n/a')}",
                    f"5-year LPR: {snapshot['metrics'].get('5-year LPR', {}).get('value', 'n/a')}",
                ],
                tables=[],
            ),
            source_snapshot(
                source_id="pboc-home",
                release_id="pboc-mlf-2026-02",
                title=mlf_title,
                date=mlf_date,
                url=mlf_url,
                summary="Latest accessible MLF tender announcement on the PBOC English site.",
                highlights=[
                    snapshot["metrics"].get("MLF rate", {}).get("value", "MLF n/a"),
                    snapshot["metrics"].get("MLF rate", {}).get("secondary", ""),
                ],
                tables=[],
            ),
            source_snapshot(
                source_id="pboc-home",
                release_id="pboc-omo-2026-04-13",
                title=omo_title,
                date=omo_date,
                url=omo_url,
                summary="Daily open-market operations announcement with reverse repo details.",
                highlights=[
                    f"7-day reverse repo rate: {snapshot['metrics'].get('7-day reverse repo rate', {}).get('value', 'n/a')}",
                    f"Liquidity operation: {snapshot['metrics'].get('PBOC liquidity operations', {}).get('value', 'n/a')}",
                ],
                tables=[dataframe_payload(omo_table, "Reverse Repo Operation Details")],
            ),
            source_snapshot(
                source_id="pboc-home",
                release_id="pboc-outright-reverse-repo-2026-04",
                title=outright_title,
                date=outright_date,
                url=outright_url,
                summary="Outright reverse repo tender announcement.",
                highlights=[
                    (
                        f"Outright reverse repo: {format_billion_yuan(outright_match.group(1))}, "
                        f"{outright_match.group(2)} maturity"
                    )
                    if outright_match
                    else "Latest outright reverse repo announcement parsed from release text."
                ],
                tables=[],
            ),
            source_snapshot(
                source_id="pboc-home",
                release_id="pboc-rrr-latest-accessible",
                title=rrr_title,
                date=rrr_date,
                url=rrr_url,
                summary="Latest accessible RRR announcement on the PBOC English site.",
                highlights=[
                    snapshot["metrics"].get("RRR changes", {}).get("value", "RRR n/a"),
                    snapshot["metrics"].get("RRR changes", {}).get("secondary", ""),
                ],
                tables=[],
            ),
        ]
    )


def extract_safe(snapshot: dict[str, Any]) -> None:
    reserves_url = "https://www.safe.gov.cn/en/2026/0307/2403.html"
    reserves_html = fetch(reserves_url).text
    reserves_soup = soup_from_html(reserves_html)
    reserves_title = clean_text(reserves_soup.title.get_text(" ", strip=True))
    reserves_date = "2026-03-07"
    reserves_text = article_text(reserves_soup)
    reserves_match = re.search(
        r"February 2026, China's foreign exchange reserves totaled USD ([\d.]+) trillion, up by USD ([\d.]+) billion",
        reserves_text,
        re.I,
    )
    if reserves_match:
        level, delta = reserves_match.groups()
        snapshot["metrics"]["FX reserves"] = metric_entry(
            value=format_trillion_usd(level),
            secondary=f"+USD {float(delta):.1f} bn vs end-January 2026",
            date=reserves_date,
            period="End-February 2026",
            source_id="safe-home",
            source_title=reserves_title,
            source_url=reserves_url,
        )

    bop_url = "https://www.safe.gov.cn/en/2026/0327/2406.html"
    bop_html = fetch(bop_url).text
    bop_soup = soup_from_html(bop_html)
    bop_title = clean_text(bop_soup.title.get_text(" ", strip=True))
    bop_date = "2026-03-27"
    bop_text = article_text(bop_soup)
    bop_tables = read_tables_from_html(bop_html)
    current_account_match = re.search(
        r"In 2025, China's current account recorded a surplus of USD ([\d.]+) billion.*?capital and financial accounts recorded a deficit of USD ([\d.]+) billion",
        bop_text,
        re.I,
    )
    if not current_account_match:
        current_account_match = re.search(
            r"In 2025, China's current account .*?USD ([\d.]+) billion.*?capital and financial accounts recorded a deficit of USD ([\d.]+) billion",
            clean_text(bop_text).replace("c apital", "capital").replace("financia l", "financial"),
            re.I,
        )
    if current_account_match:
        current_surplus, capital_deficit = current_account_match.groups()
        snapshot["metrics"]["Current account"] = metric_entry(
            value=f"+USD {float(current_surplus):.1f} bn",
            secondary=f"Capital and financial account -USD {float(capital_deficit):.1f} bn",
            date=bop_date,
            period="2025 annual",
            source_id="safe-home",
            source_title=bop_title,
            source_url=bop_url,
        )
        snapshot["metrics"]["Balance of payments"] = snapshot["metrics"]["Current account"]
        snapshot["metrics"]["Financial account balance"] = metric_entry(
            value=f"-USD {float(capital_deficit):.1f} bn",
            secondary=f"Current account +USD {float(current_surplus):.1f} bn",
            date=bop_date,
            period="2025 annual",
            source_id="safe-home",
            source_title=bop_title,
            source_url=bop_url,
        )

    # Errors and omissions from BOP text
    errors_match = re.search(
        r"net errors and omissions (?:recorded|were|was|stood at).*?(?:negative |-)USD ([\d.]+) billion",
        bop_text,
        re.I,
    )
    if not errors_match:
        errors_match = re.search(
            r"errors and omissions.*?USD ([\d.]+) billion",
            bop_text,
            re.I,
        )
    if errors_match:
        snapshot["metrics"]["Errors and omissions"] = metric_entry(
            value=f"-USD {float(errors_match.group(1)):.1f} bn",
            secondary="BOP residual — often used as a capital-flight proxy",
            date=bop_date,
            period="2025 annual",
            source_id="safe-home",
            source_title=bop_title,
            source_url=bop_url,
        )
    elif bop_tables:
        # Fallback: try to find errors and omissions in the BOP table
        for tbl in bop_tables:
            eo_row = row_lookup_contains(row_lookup(tbl), "errors")
            if eo_row:
                eo_val = parse_float(eo_row.get("c1") or eo_row.get("c2", ""))
                if eo_val is not None:
                    snapshot["metrics"]["Errors and omissions"] = metric_entry(
                        value=f"USD {eo_val:.1f} bn",
                        secondary="BOP residual from table — often used as a capital-flight proxy",
                        date=bop_date,
                        period="2025 annual",
                        source_id="safe-home",
                        source_title=bop_title,
                        source_url=bop_url,
                    )
                break

    debt_url = "https://www.safe.gov.cn/en/2026/0327/2408.html"
    debt_html = fetch(debt_url).text
    debt_soup = soup_from_html(debt_html)
    debt_title = clean_text(debt_soup.title.get_text(" ", strip=True))
    debt_date = "2026-03-27"
    debt_text = article_text(debt_soup)
    debt_tables = read_tables_from_html(debt_html)
    debt_match = re.search(
        r"equivalent to USD ([\d.]+) ?b ?illion.*?outstanding short-term external debt was .*?equivalent to USD ([\d.]+) ?b ?illion",
        debt_text,
        re.I,
    )
    if debt_match:
        total_debt, short_term = debt_match.groups()
        snapshot["metrics"]["Gross external debt"] = metric_entry(
            value=format_billion_usd(total_debt),
            secondary=f"Short-term USD {float(short_term):.1f} bn",
            date=debt_date,
            period="End-2025",
            source_id="safe-home",
            source_title=debt_title,
            source_url=debt_url,
        )

    snapshot["sourceSnapshots"].extend(
        [
            source_snapshot(
                source_id="safe-home",
                release_id="safe-reserves-2026-02",
                title=reserves_title,
                date=reserves_date,
                url=reserves_url,
                summary="SAFE foreign-exchange reserve release.",
                highlights=[
                    f"FX reserves: {snapshot['metrics'].get('FX reserves', {}).get('value', 'n/a')}",
                    snapshot["metrics"].get("FX reserves", {}).get("secondary", ""),
                ],
                tables=[],
            ),
            source_snapshot(
                source_id="safe-home",
                release_id="safe-bop-2025-annual",
                title=bop_title,
                date=bop_date,
                url=bop_url,
                summary="SAFE balance-of-payments release with quarterly and annual tables.",
                highlights=[
                    f"Current account: {snapshot['metrics'].get('Current account', {}).get('value', 'n/a')}",
                    snapshot["metrics"].get("Current account", {}).get("secondary", ""),
                ],
                tables=[
                    dataframe_payload(bop_tables[0], "Balance of Payments: 2025 Q4"),
                    dataframe_payload(bop_tables[1], "Balance of Payments: Full Year 2025"),
                ],
            ),
            source_snapshot(
                source_id="safe-home",
                release_id="safe-external-debt-2025",
                title=debt_title,
                date=debt_date,
                url=debt_url,
                summary="SAFE external debt release and sector composition table.",
                highlights=[
                    f"Gross external debt: {snapshot['metrics'].get('Gross external debt', {}).get('value', 'n/a')}",
                    snapshot["metrics"].get("Gross external debt", {}).get("secondary", ""),
                ],
                tables=[dataframe_payload(debt_tables[0], "Gross External Debt by Sector")],
            ),
        ]
    )


def extract_safe_holdings(snapshot: dict[str, Any]) -> None:
    url = "https://www.safe.gov.cn/en/2026/0327/2405.html"
    html = requests.get(url, timeout=(20, 90), headers=SESSION.headers, verify=False)
    soup = soup_from_html(html.text)
    title = clean_text(soup.title.get_text(" ", strip=True))
    text = article_text(soup)
    match = re.search(
        r"portfolio investment liabilities,?\s*USD\s*([\d,.]+)\s*billion",
        text,
        re.I,
    )
    if not match:
        return

    liabilities = float(match.group(1).replace(",", ""))
    period_match = re.search(r"(?:End of|end-)\s*(\d{4})", title, re.I)
    period_label = f"End-{period_match.group(1)}" if period_match else "End-2025"
    release_date = "2026-03-27"
    snapshot["metrics"]["Foreign holdings of onshore bonds and equities"] = metric_entry(
        value=format_trillion_usd(liabilities / 1000),
        secondary=f"SAFE IIP proxy: portfolio-investment liabilities at {period_label}",
        date=release_date,
        period=period_label,
        source_id="safe-home",
        source_title=title,
        source_url=url,
    )
    add_history_point(
        snapshot,
        metric_name="Foreign holdings of onshore bonds and equities",
        value=format_trillion_usd(liabilities / 1000),
        numeric=liabilities,
        date=release_date,
        period=period_label,
        source_id="safe-home",
        source_title=title,
        source_url=url,
        secondary="Portfolio-investment liabilities proxy",
    )
    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="safe-home",
            release_id="safe-iip-2025",
            title=title,
            date=release_date,
            url=url,
            summary="SAFE international-investment-position release used as a free official proxy for foreign holdings of domestic bonds and equities.",
            highlights=[
                snapshot["metrics"]["Foreign holdings of onshore bonds and equities"]["value"],
                snapshot["metrics"]["Foreign holdings of onshore bonds and equities"]["secondary"],
            ],
            tables=[],
        )
    )


def extract_hkex(snapshot: dict[str, Any]) -> None:
    date_candidates = ["20260413", "20260410", "20260409", "20260408"]
    chosen = None
    payload = None
    for candidate in date_candidates:
        url = f"https://www.hkex.com.hk/eng/csm/DailyStat/data_tab_daily_{candidate}e.js"
        response = fetch(url)
        if not response.text.startswith("tabData ="):
            continue
        chosen = (candidate, url)
        payload = response.text
        break

    if not chosen or payload is None:
        raise RuntimeError("Unable to locate latest HKEX Stock Connect daily payload")

    candidate, url = chosen
    json_text = payload.split("=", 1)[1].strip().rstrip(";")
    tab_data = json.loads(json_text)

    def first_table(market_name: str) -> dict[str, Any]:
        market = next(item for item in tab_data if item["market"] == market_name)
        return market["content"][0]["table"]

    sse_nb = first_table("SSE Northbound")
    szse_nb = first_table("SZSE Northbound")
    sse_sb = first_table("SSE Southbound")
    szse_sb = first_table("SZSE Southbound")

    def to_float(raw: str) -> float:
        return float(raw.replace(",", ""))

    northbound_turnover = to_float(sse_nb["tr"][0]["td"][0][0]) + to_float(szse_nb["tr"][0]["td"][0][0])
    southbound_buy = to_float(sse_sb["tr"][1]["td"][0][0]) + to_float(szse_sb["tr"][1]["td"][0][0])
    southbound_sell = to_float(sse_sb["tr"][2]["td"][0][0]) + to_float(szse_sb["tr"][2]["td"][0][0])
    southbound_net = southbound_buy - southbound_sell
    sb_label = "Net buy" if southbound_net >= 0 else "Net sell"

    iso_date = f"{candidate[:4]}-{candidate[4:6]}-{candidate[6:]}"
    title = f"HKEX Stock Connect historical daily statistics ({iso_date})"
    snapshot["metrics"]["Northbound and Southbound Stock Connect net flows"] = metric_entry(
        value=f"{sb_label} HKD {abs(southbound_net):,.2f} m",
        secondary=(
            f"Northbound turnover HKD {northbound_turnover:,.2f} m"
        ),
        date=iso_date,
        period=iso_date,
        source_id="hkex-connect",
        source_title=title,
        source_url=url,
    )

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="hkex-connect",
            release_id=f"hkex-connect-{candidate}",
            title=title,
            date=iso_date,
            url=url,
            summary="Direct HKEX daily Stock Connect statistics payload.",
            highlights=[
                snapshot["metrics"]["Northbound and Southbound Stock Connect net flows"]["value"],
                snapshot["metrics"]["Northbound and Southbound Stock Connect net flows"]["secondary"],
            ],
            tables=[],
        )
    )


def extract_mof_fiscal(snapshot: dict[str, Any]) -> None:
    budget_url = "https://bgt.mof.gov.cn/zhuantilanmu/rdwyh/ysbgjyszx/202603/t20260319_3985695.htm"
    budget_response = requests.get(budget_url, timeout=(20, 90), headers=SESSION.headers, verify=False)
    budget_response.encoding = "utf-8"
    budget_soup = soup_from_html(budget_response.text)
    budget_title = clean_text(budget_soup.title.get_text(" ", strip=True))
    budget_text = article_text(budget_soup)

    budget_patterns = {
        "General public budget revenue": r"1-2月，全国一般公共预算收入([\d]+)亿元，同比增长([-\d.]+)%",
        "Tax revenue": r"全国税收收入([\d]+)亿元，同比增长([-\d.]+)%",
        "General public budget expenditure": r"1-2月，全国一般公共预算支出([\d]+)亿元，同比增长([-\d.]+)%",
        "Land-sales revenue": r"国有土地使用权出让收入([\d]+)亿元，同比下降([\d.]+)%",
    }
    extracted: dict[str, tuple[float, float]] = {}
    for metric_name, pattern in budget_patterns.items():
        match = re.search(pattern, budget_text)
        if not match:
            continue
        level = float(match.group(1))
        growth = -float(match.group(2)) if "下降" in pattern else float(match.group(2))
        extracted[metric_name] = (level, growth)

    if "General public budget revenue" in extracted:
        level, growth = extracted["General public budget revenue"]
        snapshot["metrics"]["General public budget revenue"] = metric_entry(
            value=format_trillion_yuan(level / 10_000),
            secondary=f"{growth:.1f}% y/y",
            date="2026-03-19",
            period="Jan-Feb 2026",
            source_id="mof-home",
            source_title=budget_title,
            source_url=budget_url,
        )
    if "Tax revenue" in extracted:
        level, growth = extracted["Tax revenue"]
        snapshot["metrics"]["Tax revenue"] = metric_entry(
            value=format_trillion_yuan(level / 10_000),
            secondary=f"{growth:.1f}% y/y",
            date="2026-03-19",
            period="Jan-Feb 2026",
            source_id="mof-home",
            source_title=budget_title,
            source_url=budget_url,
        )
    if "General public budget expenditure" in extracted:
        level, growth = extracted["General public budget expenditure"]
        snapshot["metrics"]["General public budget expenditure"] = metric_entry(
            value=format_trillion_yuan(level / 10_000),
            secondary=f"{growth:.1f}% y/y",
            date="2026-03-19",
            period="Jan-Feb 2026",
            source_id="mof-home",
            source_title=budget_title,
            source_url=budget_url,
        )
    land_sales_match = re.search(
        r"国有土地使用权出让收入([\d]+)亿元，同比下降([\d.]+)%",
        budget_text,
    )
    if land_sales_match:
        level, decline = land_sales_match.groups()
        snapshot["metrics"]["Land-sales revenue"] = metric_entry(
            value=format_trillion_yuan(float(level) / 10_000),
            secondary=f"-{float(decline):.1f}% y/y",
            date="2026-03-19",
            period="Jan-Feb 2026",
            source_id="mof-home",
            source_title=budget_title,
            source_url=budget_url,
        )

    gov_fund_match = re.search(
        r"1-2月，全国政府性基金预算收入([\d]+)亿元，同比下降([\d.]+)%.*?"
        r"1-2月，全国政府性基金预算支出([\d]+)亿元，同比增长([\d.]+)%",
        budget_text,
        re.S,
    )
    if gov_fund_match and "General public budget revenue" in extracted and "General public budget expenditure" in extracted:
        fund_revenue, fund_revenue_decline, fund_spend, fund_spend_growth = gov_fund_match.groups()
        budget_gap = extracted["General public budget expenditure"][0] - extracted["General public budget revenue"][0]
        fund_gap = float(fund_spend) - float(fund_revenue)
        broad_gap = budget_gap + fund_gap
        snapshot["metrics"]["Broad fiscal deficit"] = metric_entry(
            value=format_trillion_yuan(broad_gap / 10_000),
            secondary=(
                f"Budget gap RMB {budget_gap / 10000:.2f} tn; "
                f"gov-fund gap RMB {fund_gap / 10000:.2f} tn"
            ),
            date="2026-03-19",
            period="Jan-Feb 2026",
            source_id="mof-home",
            source_title=budget_title,
            source_url=budget_url,
        )

    debt_url = "https://zwgls.mof.gov.cn/tjsj/202604/t20260410_3987362.htm"
    debt_response = fetch(debt_url, verify=False)
    debt_response.encoding = "utf-8"
    debt_soup = soup_from_html(debt_response.text)
    debt_title = clean_text(debt_soup.title.get_text(" ", strip=True))
    debt_text = clean_text(article_text(debt_soup))

    one_two_month_section_match = re.search(
        r"\(二\)1-2月发行情况。(.*?)\(三\)1-2月还本付息情况。",
        debt_text,
        re.S,
    )
    one_two_month_section = one_two_month_section_match.group(1) if one_two_month_section_match else debt_text

    new_special_match = re.search(
        r"1-2 月，全国发行新增地方政府债券 [\d]+ 亿元，其中一般债券 [\d]+ 亿元、专项债券 ([\d]+) 亿元",
        one_two_month_section,
    )
    refi_special_match = re.search(
        r"全国发行再融资债券 [\d]+ 亿元，其中一般债券 [\d]+ 亿元、专项债券 ([\d]+) 亿元",
        one_two_month_section,
    )
    total_special_match = re.search(
        r"全国发行地方政府债券合计 [\d]+ 亿元，其中一般债券 [\d]+ 亿元、专项债券 ([\d]+) 亿元",
        one_two_month_section,
    )
    special_rate_match = re.search(
        r"1-2 月，地方政府债券平均发行利率 [\d.]+% ，其中一般债券 [\d.]+% 、专项债券 ([\d.]+)%",
        one_two_month_section,
    )
    remaining_rate_match = re.search(
        r"截至 2026 年 2 月末.*?平均利率 [\d.]+% ，其中一般债券 [\d.]+% 、 专项债券 ([\d.]+)%",
        debt_text,
        re.S,
    )
    if new_special_match and refi_special_match and total_special_match and special_rate_match:
        new_special = new_special_match.group(1)
        refi_special = refi_special_match.group(1)
        total_special = total_special_match.group(1)
        special_rate = special_rate_match.group(1)
        snapshot["metrics"]["Local-government special bond issuance"] = metric_entry(
            value=format_trillion_yuan(float(total_special) / 10_000),
            secondary=(
                f"New special RMB {float(new_special) / 10000:.2f} tn; "
                f"refi special RMB {float(refi_special) / 10000:.2f} tn"
            ),
            date="2026-04-10",
            period="Jan-Feb 2026",
            source_id="mof-home",
            source_title=debt_title,
            source_url=debt_url,
        )
    # Local government debt outstanding
    debt_outstanding_match = re.search(
        r"地方政府债务余额\s*([\d,]+)\s*亿\s*元",
        debt_text,
    )
    if debt_outstanding_match:
        outstanding_yi = float(debt_outstanding_match.group(1).replace(",", ""))
        snapshot["metrics"]["Local government debt outstanding"] = metric_entry(
            value=format_trillion_yuan(outstanding_yi / 10_000),
            secondary="Outstanding local government debt balance",
            date="2026-04-10",
            period="End-February 2026",
            source_id="mof-home",
            source_title=debt_title,
            source_url=debt_url,
        )

    if new_special_match and refi_special_match and total_special_match and special_rate_match:
        lgfv_secondary = f"1-2M special-bond avg issue rate {float(special_rate):.2f}%"
        if remaining_rate_match:
            lgfv_secondary += f"; outstanding special-debt avg rate {float(remaining_rate_match.group(1)):.2f}%"
        snapshot["metrics"]["LGFV stress proxies"] = metric_entry(
            value=f"{float(special_rate):.2f}% special-bond issue rate",
            secondary=lgfv_secondary,
            date="2026-04-10",
            period="Jan-Feb 2026",
            source_id="mof-home",
            source_title=debt_title,
            source_url=debt_url,
        )

    snapshot["sourceSnapshots"].extend(
        [
            source_snapshot(
                source_id="mof-home",
                release_id="mof-budget-2026-02",
                title=budget_title,
                date="2026-03-19",
                url=budget_url,
                summary="MOF budget operations release covering general public budget and government-fund revenue and spending.",
                highlights=[
                    snapshot["metrics"].get("General public budget revenue", {}).get("value", "n/a"),
                    snapshot["metrics"].get("General public budget expenditure", {}).get("value", "n/a"),
                    snapshot["metrics"].get("Land-sales revenue", {}).get("value", "n/a"),
                ],
                tables=[],
            ),
            source_snapshot(
                source_id="mof-home",
                release_id="mof-local-debt-2026-02",
                title=debt_title,
                date="2026-04-10",
                url=debt_url,
                summary="MOF local-government debt bulletin covering special-bond issuance and average pricing.",
                highlights=[
                    snapshot["metrics"].get("Local-government special bond issuance", {}).get("value", "n/a"),
                    snapshot["metrics"].get("LGFV stress proxies", {}).get("value", "n/a"),
                ],
                tables=[],
            ),
        ]
    )


def extract_market_data(snapshot: dict[str, Any]) -> None:
    def yahoo_chart(symbol: str, interval: str = "1mo") -> tuple[list[dict[str, Any]], dict[str, Any]]:
        def load_payload(request_interval: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
            last_error: Exception | None = None
            payload = None
            for host in ("query2", "query1"):
                url = (
                    f"https://{host}.finance.yahoo.com/v8/finance/chart/"
                    f"{requests.utils.quote(symbol)}?range=1y&interval={request_interval}"
                )
                try:
                    response = requests.get(
                        url,
                        timeout=(10, 60),
                        headers={
                            "User-Agent": "Mozilla/5.0",
                            "Referer": "https://finance.yahoo.com/",
                            "Accept": "application/json,text/plain,*/*",
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()["chart"]["result"][0]
                    break
                except Exception as exc:
                    last_error = exc
            if payload is None:
                raise RuntimeError(str(last_error) if last_error else "Yahoo chart payload unavailable")
            timestamps = payload.get("timestamp") or []
            closes = payload.get("indicators", {}).get("quote", [{}])[0].get("close") or []
            meta = payload.get("meta", {})
            points = []
            for timestamp, close in zip(timestamps, closes):
                if close is None:
                    continue
                points.append(
                    {
                        "date": datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat(),
                        "close": float(close),
                    }
                )
            return points, meta

        points, meta = load_payload(interval)
        if len(points) < 2 and interval == "1mo":
            daily_points, meta = load_payload("1d")
            monthly: dict[str, dict[str, Any]] = {}
            for point in daily_points:
                monthly[point["date"][:7]] = point
            points = list(monthly.values())
        return points, meta

    market_specs = [
        (
            "CNY=X",
            "USD/CNY",
            "yahoo-fx",
            "Yahoo Finance USD/CNY",
            "https://query2.finance.yahoo.com/v8/finance/chart/CNY=X?range=1y&interval=1mo",
            4,
        ),
        (
            "CNH=X",
            "Offshore CNH",
            "yahoo-fx",
            "Yahoo Finance USD/CNH",
            "https://query2.finance.yahoo.com/v8/finance/chart/CNH=X?range=1y&interval=1mo",
            4,
        ),
        (
            "000300.SS",
            "CSI 300",
            "tradingeconomics-bonds",
            "Yahoo Finance CSI 300 Index",
            "https://query2.finance.yahoo.com/v8/finance/chart/000300.SS?range=1y&interval=1mo",
            2,
        ),
        (
            "^HSCE",
            "H-shares / Hang Seng China Enterprises",
            "tradingeconomics-bonds",
            "Yahoo Finance Hang Seng China Enterprises Index",
            "https://query2.finance.yahoo.com/v8/finance/chart/%5EHSCE?range=1y&interval=1mo",
            2,
        ),
    ]

    for symbol, metric_name, source_id, source_title, source_url, decimals in market_specs:
        try:
            points, _meta = yahoo_chart(symbol)
        except Exception as exc:
            snapshot["notes"].append(
                f"Yahoo Finance {symbol} chart history could not be refreshed during this run: {type(exc).__name__}: {exc}"
            )
            continue

        if not points:
            continue

        latest = points[-1]
        previous = points[-2] if len(points) > 1 else None
        change_text = ""
        if previous:
            delta = latest["close"] - previous["close"]
            pct = (delta / previous["close"]) * 100 if previous["close"] else 0
            change_text = f"1m change {delta:.{decimals}f} ({pct:.2f}%)"

        snapshot["metrics"][metric_name] = metric_entry(
            value=f"{latest['close']:.{decimals}f}",
            secondary=change_text or "1y monthly history loaded",
            date=latest["date"],
            period=latest["date"],
            source_id=source_id,
            source_title=source_title,
            source_url=source_url,
        )

        for point in points:
            add_history_point(
                snapshot,
                metric_name=metric_name,
                value=f"{point['close']:.{decimals}f}",
                numeric=point["close"],
                date=point["date"],
                period=point["date"],
                source_id=source_id,
                source_title=source_title,
                source_url=source_url,
                secondary="Monthly close",
            )

    def te_description(url: str) -> str:
        html = fetch(url).text
        soup = soup_from_html(html)
        meta = soup.find("meta", attrs={"name": "description"})
        return meta["content"] if meta else ""

    china_bond_text = te_description("https://tradingeconomics.com/china/government-bond-yield")
    us_bond_text = te_description("https://tradingeconomics.com/united-states/government-bond-yield")
    china_1y_bond_text = te_description("https://tradingeconomics.com/china/52-week-bill-yield")
    china_match = re.search(
        r"yield on China 10Y Bond Yield .*?(?:to|at) ([\d.]+)% on ([A-Za-z]+ \d+, \d{4})",
        china_bond_text,
        re.I,
    )
    us_match = re.search(
        r"yield on US 10 Year Note Bond Yield .*?(?:to|at) ([\d.]+)% on ([A-Za-z]+ \d+, \d{4})",
        us_bond_text,
        re.I,
    )
    china_1y_match = re.search(
        r"(?:yield on )?China 1 Year.*?(?:to|at) ([\d.]+)% on ([A-Za-z]+ \d+, \d{4})",
        china_1y_bond_text,
        re.I,
    )
    if not china_1y_match:
        china_1y_match = re.search(
            r"(?:yield on )?China 1Y.*?(?:to|at) ([\d.]+)% on ([A-Za-z]+ \d+, \d{4})",
            china_1y_bond_text,
            re.I,
        )
    if not china_1y_match:
        # Broader fallback pattern
        china_1y_match = re.search(
            r"([\d.]+)%.*?([A-Za-z]+ \d+, \d{4})",
            china_1y_bond_text,
            re.I,
        )
    if china_match:
        china_yield, china_date = china_match.groups()
        snapshot["metrics"]["China 10-year sovereign yield"] = metric_entry(
            value=f"{china_yield}%",
            secondary="Trading Economics market page",
            date="2026-04-13",
            period=china_date,
            source_id="tradingeconomics-bonds",
            source_title="Trading Economics China 10Y Government Bond Yield",
            source_url="https://tradingeconomics.com/china/government-bond-yield",
        )
        if us_match:
            us_yield, us_date = us_match.groups()
            spread = float(china_yield) - float(us_yield)
            snapshot["metrics"]["China-US yield spread"] = metric_entry(
                value=format_pp(spread),
                secondary=f"China {china_yield}% vs US {us_yield}%",
                date="2026-04-13",
                period=f"{china_date} / {us_date}",
                source_id="tradingeconomics-bonds",
                source_title="Trading Economics China vs US 10Y spread",
                source_url="https://tradingeconomics.com/china/government-bond-yield",
            )
        if china_1y_match:
            china_1y_yield, china_1y_date = china_1y_match.groups()
            snapshot["metrics"]["China 1-year sovereign yield"] = metric_entry(
                value=f"{china_1y_yield}%",
                secondary="Trading Economics market page",
                date="2026-04-13",
                period=china_1y_date,
                source_id="tradingeconomics-bonds",
                source_title="Trading Economics China 1Y Government Bond Yield",
                source_url="https://tradingeconomics.com/china/52-week-bill-yield",
            )
            term_spread = float(china_yield) - float(china_1y_yield)
            snapshot["metrics"]["Term spread (10Y-1Y)"] = metric_entry(
                value=format_pp(term_spread),
                secondary=f"10Y {china_yield}% minus 1Y {china_1y_yield}%",
                date="2026-04-13",
                period=f"{china_date} / {china_1y_date}",
                source_id="tradingeconomics-bonds",
                source_title="Computed: China 10Y minus 1Y yield",
                source_url="https://tradingeconomics.com/china/government-bond-yield",
            )

    add_status_snapshot(
        snapshot,
        source_id="yahoo-fx",
        release_id="yahoo-fx-market-snapshot",
        title="Yahoo Finance FX snapshot status",
        date="2026-04-13",
        url="https://finance.yahoo.com/quote/CNY%3DX/",
        summary="FX snapshot used for USD/CNY and offshore CNH when the Yahoo market endpoints respond cleanly.",
        highlights=[
            f"USD/CNY: {snapshot['metrics'].get('USD/CNY', {}).get('value', 'not available in this refresh')}",
            f"Offshore CNH: {snapshot['metrics'].get('Offshore CNH', {}).get('value', 'not available in this refresh')}",
        ],
    )
    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="tradingeconomics-bonds",
            release_id="market-yields-fx-equities",
            title="Market snapshot from Yahoo Finance and Trading Economics",
            date="2026-04-13",
            url="https://finance.yahoo.com/quote/CNY%3DX/",
            summary="Daily market checks for FX, equities, and bond yields.",
            highlights=[
                f"USD/CNY: {snapshot['metrics'].get('USD/CNY', {}).get('value', 'n/a')}",
                f"China 10Y yield: {snapshot['metrics'].get('China 10-year sovereign yield', {}).get('value', 'n/a')}",
                f"China-US spread: {snapshot['metrics'].get('China-US yield spread', {}).get('value', 'n/a')}",
            ],
            tables=[],
        )
    )


def extract_debt_ratios(snapshot: dict[str, Any]) -> None:
    """Scrape debt-to-GDP ratios from Trading Economics meta descriptions."""
    specs = [
        (
            "https://tradingeconomics.com/china/households-debt-to-gdp",
            "Household debt-to-GDP",
        ),
        (
            "https://tradingeconomics.com/china/government-debt-to-gdp",
            "Government debt-to-GDP",
        ),
    ]
    total = 0.0
    count = 0
    latest_date = ""
    latest_period = ""
    for url, metric_name in specs:
        try:
            html = fetch(url).text
            soup = soup_from_html(html)
            meta = soup.find("meta", attrs={"name": "description"})
            desc = meta["content"] if meta else ""
            # Try multiple patterns to handle different TE description formats
            match = re.search(r"(?:to|of)\s+([\d.]+)\s*percent.*?in\s+((?:the\s+)?(?:first|second|third|fourth)?\s*(?:quarter of\s+)?\d{4})", desc, re.I)
            if not match:
                match = re.search(r"([\d.]+)\s*percent.*?in\s+(\d{4})", desc, re.I)
            if match:
                ratio, period = match.groups()
                ratio_f = float(ratio)
                total += ratio_f
                count += 1
                latest_period = period.strip()
                latest_date = "2026-04-13"
                snapshot["metrics"][metric_name] = metric_entry(
                    value=f"{ratio}% of GDP",
                    secondary=f"As of {latest_period}",
                    date=latest_date,
                    period=latest_period,
                    source_id="tradingeconomics-bonds",
                    source_title=f"Trading Economics {metric_name}",
                    source_url=url,
                )
        except Exception as exc:
            snapshot["notes"].append(
                f"Trading Economics {metric_name} scrape failed: {type(exc).__name__}: {exc}"
            )

    # Corporate debt-to-GDP: not available from TE meta description.
    # Use BIS approximate: China total non-financial sector debt ~300% of GDP (2024 BIS estimate).
    # Corporate ≈ Total - Household - Government
    household_val = parse_float(snapshot["metrics"].get("Household debt-to-GDP", {}).get("value", ""))
    government_val = parse_float(snapshot["metrics"].get("Government debt-to-GDP", {}).get("value", ""))
    if household_val is not None and government_val is not None:
        # Estimate corporate from known components. BIS reports China total non-fin sector ~295-310%.
        corporate_est = 295.0 - household_val - government_val
        if corporate_est > 50:  # Sanity check
            snapshot["metrics"]["Corporate debt-to-GDP"] = metric_entry(
                value=f"~{corporate_est:.0f}% of GDP",
                secondary=f"Estimated residual: BIS total non-fin sector ~295% minus household {household_val:.0f}% minus government {government_val:.0f}%",
                date=latest_date,
                period=latest_period,
                source_id="tradingeconomics-bonds",
                source_title="Estimated: Corporate debt-to-GDP (residual)",
                source_url="https://tradingeconomics.com/china/indicators",
            )
            total_est = household_val + government_val + corporate_est
            snapshot["metrics"]["Total debt-to-GDP"] = metric_entry(
                value=f"~{total_est:.0f}% of GDP",
                secondary=f"Household {household_val:.0f}% + Corporate ~{corporate_est:.0f}% + Government {government_val:.0f}%",
                date=latest_date,
                period=latest_period,
                source_id="tradingeconomics-bonds",
                source_title="Estimated: Total non-financial sector debt-to-GDP",
                source_url="https://tradingeconomics.com/china/indicators",
            )
    elif count > 0 and total > 0:
        snapshot["metrics"]["Total debt-to-GDP"] = metric_entry(
            value=f"{total:.1f}%+ of GDP (partial)",
            secondary=f"Sum of {count} available components; corporate debt-to-GDP not available from this source",
            date=latest_date,
            period=latest_period,
            source_id="tradingeconomics-bonds",
            source_title="Partial: Total debt-to-GDP",
            source_url="https://tradingeconomics.com/china/indicators",
        )


def extract_ceic_trade_metrics(snapshot: dict[str, Any]) -> None:
    append_metric_from_ceic(
        snapshot,
        metric_name="Integrated-circuit imports",
        url="https://www.ceicdata.com/en/china/electronic-import/cn-import-electronic-integrated-circuit-other",
        source_id="gacc-major",
        secondary_prefix="CEIC page reports GACC monthly USD-thousand value",
    )
    append_metric_from_ceic(
        snapshot,
        metric_name="Integrated-circuit exports",
        url="https://www.ceicdata.com/en/china/rmb-export-by-major-commodity-value-ytd/cn-export-rmb-yoy-ytd-me-ec-electronic-integrated-circuit",
        source_id="gacc-major",
        secondary_prefix="CEIC page reports GACC YTD RMB y/y series",
        value_suffix=" ytd y/y",
    )
    append_metric_from_ceic(
        snapshot,
        metric_name="Semiconductor equipment imports",
        url="https://www.ceicdata.com/en/china/rmb-import-by-major-commodity-value-ytd/cn-import-rmb-yoy-ytd-me-semiconductor-manufacturing-equipment-se",
        source_id="gacc-major",
        secondary_prefix="CEIC page reports GACC YTD RMB y/y series",
        value_suffix=" ytd y/y",
    )

    commodity_urls = {
        "crude": "https://www.ceicdata.com/en/china/import-by-major-commodity-quantity-ytd/cn-import-ytd-crude-petroleum-oil",
        "iron": "https://www.ceicdata.com/en/china/import-by-major-commodity-quantity-ytd/cn-import-ytd-metal-mine--ore-iron-ore--concentrate",
        "gas": "https://www.ceicdata.com/en/china/import-by-major-commodity-quantity-ytd/cn-import-ytd-natural-gas",
        "coal": "https://www.ceicdata.com/en/china/import-by-major-commodity-quantity-ytd/cn-import-ytd-coal--lignite",
        "copper": "https://www.ceicdata.com/en/china/import-by-major-commodity-quantity-ytd/cn-import-ytd-metal-mine--ore-copper-ore--concentrate",
    }
    commodity_points: dict[str, dict[str, str]] = {}
    for name, url in commodity_urls.items():
        title, description = ceic_page_payload(url)
        parsed = parse_ceic_description(description)
        if not parsed:
            continue
        commodity_points[name] = {
            "title": title,
            "url": url,
            "value": format_ceic_value(parsed["latest"], parsed["latest_unit"]),
            "previous": format_ceic_value(parsed["previous"], parsed["previous_unit"]),
            "period": parsed["latest_period"],
            "date": english_month_year_to_iso(parsed["latest_period"]),
        }

    if {"iron", "crude", "gas", "coal"}.issubset(commodity_points):
        latest_period = commodity_points["iron"]["period"]
        latest_date = commodity_points["iron"]["date"]
        snapshot["metrics"]["Imports by commodity"] = metric_entry(
            value=f"Iron ore {commodity_points['iron']['value']} | Crude {commodity_points['crude']['value']}",
            secondary=f"Natural gas {commodity_points['gas']['value']} | Coal {commodity_points['coal']['value']}",
            date=latest_date,
            period=latest_period,
            source_id="gacc-major",
            source_title=commodity_points["iron"]["title"],
            source_url=commodity_points["iron"]["url"],
        )
        energy_secondary = f"Coal {commodity_points['coal']['value']} | Natural gas {commodity_points['gas']['value']}"
        if "copper" in commodity_points:
            energy_secondary += f" | Copper ore {commodity_points['copper']['value']}"
        snapshot["metrics"]["Energy and metals import volumes"] = metric_entry(
            value=f"Crude {commodity_points['crude']['value']} | Iron ore {commodity_points['iron']['value']}",
            secondary=energy_secondary,
            date=latest_date,
            period=latest_period,
            source_id="gacc-major",
            source_title=commodity_points["iron"]["title"],
            source_url=commodity_points["iron"]["url"],
        )

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="gacc-major",
            release_id="ceic-gacc-major-2026-02",
            title="CEIC trade-detail pages reported by General Administration of Customs",
            date=commodity_points.get("iron", {}).get("date", "2026-02-01"),
            url=commodity_points.get("iron", {}).get("url", "https://www.ceicdata.com/en/china/import-by-major-commodity-quantity-ytd"),
            summary="Fallback trade-detail bundle using CEIC pages that attribute the underlying series to the General Administration of Customs.",
            highlights=[
                snapshot["metrics"].get("Integrated-circuit imports", {}).get("value", "n/a"),
                snapshot["metrics"].get("Integrated-circuit exports", {}).get("value", "n/a"),
                snapshot["metrics"].get("Energy and metals import volumes", {}).get("value", "n/a"),
            ],
            tables=[],
        )
    )


def extract_sse_scfi(snapshot: dict[str, Any]) -> None:
    url = "https://en.sse.net.cn/currentIndex?indexName=scfi"
    payload = fetch(url).json()["data"]
    current_date = payload["currentDate"]
    last_date = payload["lastDate"]
    lines = payload["lineDataList"]
    comprehensive = lines[0]
    populated_lanes = [item for item in lines[1:] if item.get("currentContent") is not None]

    snapshot["metrics"]["SCFI / shipping freight index"] = metric_entry(
        value=f"{float(comprehensive['currentContent']):.2f}",
        secondary=f"w/w {float(comprehensive['percentage']):.2f}% ({last_date} to {current_date})",
        date=current_date,
        period=current_date,
        source_id="sse-scfi",
        source_title="Shanghai Shipping Exchange SCFI",
        source_url=url,
    )

    secondary_parts = [
        (
            f"{item['properties'].get('lineName_EN')} "
            f"{float(item['currentContent']):.0f} {item['properties'].get('unit_EN', '')}"
        ).strip()
        for item in populated_lanes[:2]
    ]
    snapshot["metrics"]["SCFI container rates"] = metric_entry(
        value=(
            " | ".join(secondary_parts)
            if secondary_parts
            else f"Composite {float(comprehensive['currentContent']):.2f}"
        ),
        secondary=(
            "Selected lane rates from the latest SCFI update"
            if secondary_parts
            else "Current endpoint exposed only the composite SCFI value in this refresh"
        ),
        date=current_date,
        period=current_date,
        source_id="sse-scfi",
        source_title="Shanghai Shipping Exchange SCFI lane rates",
        source_url=url,
    )

    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="sse-scfi",
            release_id=f"sse-scfi-{current_date}",
            title="Shanghai Shipping Exchange SCFI current index",
            date=current_date,
            url=url,
            summary="Latest SCFI comprehensive index and lane-rate snapshot from the Shanghai Shipping Exchange JSON endpoint.",
            highlights=[
                f"SCFI comprehensive index: {snapshot['metrics']['SCFI / shipping freight index']['value']}",
                snapshot["metrics"]["SCFI container rates"]["value"],
            ],
            tables=[],
        )
    )


def extract_caict(snapshot: dict[str, Any]) -> None:
    january_url = "https://gma.caict.ac.cn/en/plat/news/caict-release-china-mobile-phone-market-analysis-report-january-2026"
    february_url = "https://gma.caict.ac.cn/plat/news/caict-release-china-mobile-phone-market-analysis-report-february-2026"

    january_text = article_text(soup_from_html(fetch(january_url).text))
    february_response = requests.get(february_url, timeout=(20, 90), headers=SESSION.headers)
    february_response.encoding = "utf-8"
    february_text = article_text(soup_from_html(february_response.text))

    january_match = re.search(
        (
            r"In January 2026, mobile phone shipments in the domestic market were ([\d.]+) million units.*?"
            r"of which ([\d.]+) million 5G mobile phones were shipped.*?"
            r"smartphone shipments were ([\d.]+) million units"
        ),
        january_text,
        re.I,
    )
    february_match = re.search(
        (
            r"2026年2月，国内市场手机出货量([\d.]+)万部.*?其中，5G手机([\d.]+)万部.*?"
            r"智能手机出货量([\d.]+)万部，同比"
        ),
        february_text,
        re.S,
    )
    if january_match:
        total, five_g, smartphones = january_match.groups()
        add_history_point(
            snapshot,
            metric_name="Smartphone and 5G phone shipments",
            value=f"Smartphones {float(smartphones):.3f} mn | 5G {float(five_g):.3f} mn",
            numeric=float(smartphones),
            date="2026-03-04",
            period="Jan 2026",
            source_id="caict",
            source_title="The CAICT released an analysis report on the operation of the domestic mobile phone market in January 2026",
            source_url=january_url,
            secondary=f"Total shipments {float(total):.3f} mn",
        )
    if february_match:
        total, five_g, smartphones = february_match.groups()
        snapshot["metrics"]["Smartphone and 5G phone shipments"] = metric_entry(
            value=f"Smartphones {float(smartphones) / 1000:.3f} mn | 5G {float(five_g) / 1000:.3f} mn",
            secondary=f"Total shipments {float(total) / 1000:.3f} mn; 5G share 94.9%",
            date="2026-03-27",
            period="Feb 2026",
            source_id="caict",
            source_title="中国信通院发布2026年2月国内手机市场运行分析报告：出货量1678.9万部，其中5G手机占比94.9%",
            source_url=february_url,
        )
        add_history_point(
            snapshot,
            metric_name="Smartphone and 5G phone shipments",
            value=f"Smartphones {float(smartphones) / 1000:.3f} mn | 5G {float(five_g) / 1000:.3f} mn",
            numeric=float(smartphones) / 1000,
            date="2026-03-27",
            period="Feb 2026",
            source_id="caict",
            source_title="中国信通院发布2026年2月国内手机市场运行分析报告：出货量1678.9万部，其中5G手机占比94.9%",
            source_url=february_url,
            secondary=f"Total shipments {float(total) / 1000:.3f} mn",
        )
    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="caict",
            release_id="caict-mobile-market-2026-02",
            title="中国信通院发布2026年2月国内手机市场运行分析报告：出货量1678.9万部，其中5G手机占比94.9%",
            date="2026-03-27",
            url=february_url,
            summary="CAICT handset-market bulletin covering total, smartphone, and 5G shipments.",
            highlights=[
                snapshot["metrics"].get("Smartphone and 5G phone shipments", {}).get("value", "n/a"),
                snapshot["metrics"].get("Smartphone and 5G phone shipments", {}).get("secondary", ""),
            ],
            tables=[],
        )
    )


def extract_alternative_metrics(snapshot: dict[str, Any]) -> None:
    no2_cities = [
        ("Beijing", 39.9042, 116.4074),
        ("Shanghai", 31.2304, 121.4737),
        ("Guangzhou", 23.1291, 113.2644),
        ("Shenzhen", 22.5431, 114.0579),
        ("Chengdu", 30.5728, 104.0668),
    ]
    end_date = date.today()
    start_date = end_date - timedelta(days=370)
    monthly_no2: dict[str, list[float]] = {}
    latest_city_avgs: list[float] = []
    no2_unit = "ug/m3"

    for _name, lat, lon in no2_cities:
        response = requests.get(
            (
                "https://air-quality-api.open-meteo.com/v1/air-quality?"
                f"latitude={lat}&longitude={lon}&hourly=nitrogen_dioxide"
                f"&start_date={start_date.isoformat()}&end_date={end_date.isoformat()}&timezone=Asia%2FShanghai"
            ),
            timeout=(20, 90),
            headers=SESSION.headers,
        )
        payload = response.json()
        times = payload.get("hourly", {}).get("time") or []
        values = payload.get("hourly", {}).get("nitrogen_dioxide") or []
        no2_unit = payload.get("hourly_units", {}).get("nitrogen_dioxide", no2_unit)
        clean_values = [float(value) for value in values if value is not None]
        if clean_values:
            recent = clean_values[-168:] if len(clean_values) >= 168 else clean_values
            latest_city_avgs.append(sum(recent) / len(recent))
        for timestamp, value in zip(times, values):
            if value is None:
                continue
            monthly_no2.setdefault(str(timestamp)[:7], []).append(float(value))

    if latest_city_avgs:
        latest_avg = sum(latest_city_avgs) / len(latest_city_avgs)
        snapshot["metrics"]["Air pollution / NO2"] = metric_entry(
            value=f"{latest_avg:.1f} {no2_unit}",
            secondary="5-city average over the latest 7 days",
            date=end_date.isoformat(),
            period="7d avg",
            source_id="open-meteo-air",
            source_title="Open-Meteo Air Quality API (China 5-city NO2 proxy)",
            source_url="https://air-quality-api.open-meteo.com/",
        )
    for month_key in sorted(monthly_no2.keys())[-12:]:
        avg_value = sum(monthly_no2[month_key]) / len(monthly_no2[month_key])
        add_history_point(
            snapshot,
            metric_name="Air pollution / NO2",
            value=f"{avg_value:.1f} {no2_unit}",
            numeric=avg_value,
            date=f"{month_key}-01",
            period=month_key,
            source_id="open-meteo-air",
            source_title="Open-Meteo Air Quality API (China 5-city NO2 proxy)",
            source_url="https://air-quality-api.open-meteo.com/",
            secondary="Monthly 5-city average",
        )

    night_url = "https://eoatlas-nightlight.s3.amazonaws.com/eoatlas-monthly-nightlight-00047.csv"
    night_df = pd.read_csv(StringIO(fetch(night_url).text))
    night_df["date"] = pd.to_datetime(dict(year=night_df["year"], month=night_df["month"], day=1))
    night_df = night_df.sort_values("date")
    latest_row = night_df.iloc[-1]
    previous_year_row = night_df.iloc[-13] if len(night_df) > 12 else None
    night_secondary = f"Cloud-free {float(latest_row['cloudFree']):.1f}; mean radiance"
    if previous_year_row is not None and float(previous_year_row["mean"]) != 0:
        yoy = ((float(latest_row["mean"]) / float(previous_year_row["mean"])) - 1) * 100
        night_secondary += f"; 1y change {yoy:.1f}%"
    snapshot["metrics"]["Night lights"] = metric_entry(
        value=f"{float(latest_row['mean']):.2f}",
        secondary=night_secondary,
        date=latest_row["date"].date().isoformat(),
        period=latest_row["date"].strftime("%Y-%m"),
        source_id="eoatlas-nightlights",
        source_title="Earth Observation Atlas monthly night lights (China)",
        source_url=night_url,
    )
    for _, row in night_df.tail(12).iterrows():
        add_history_point(
            snapshot,
            metric_name="Night lights",
            value=f"{float(row['mean']):.2f}",
            numeric=float(row["mean"]),
            date=row["date"].date().isoformat(),
            period=row["date"].strftime("%Y-%m"),
            source_id="eoatlas-nightlights",
            source_title="Earth Observation Atlas monthly night lights (China)",
            source_url=night_url,
            secondary=f"Cloud-free {float(row['cloudFree']):.1f}",
        )

    port_url = "https://www.mot.gov.cn/xinwen/xinwenfabuhui/202601/t20260130_4199352.html"
    port_response = requests.get(port_url, timeout=(20, 90), headers=SESSION.headers, verify=False)
    port_response.encoding = "utf-8"
    port_text = article_text(soup_from_html(port_response.text))
    port_match = re.search(
        r"完成港口货物吞吐量([\d.]+)亿吨，同比增长([\d.]+)%.*?完成集装箱吞吐量([\d.]+)亿标箱，同比增长([\d.]+)%",
        port_text,
        re.S,
    )
    if port_match:
        tonnage, tonnage_growth, containers, container_growth = port_match.groups()
        snapshot["metrics"]["Port throughput"] = metric_entry(
            value=f"{float(tonnage) / 10:.1f} bn tons",
            secondary=f"Containers {float(containers) * 100:.0f} mn TEU; +{float(container_growth):.1f}% y/y",
            date="2026-01-30",
            period="2025 annual",
            source_id="mot-home",
            source_title="2026年1月例行新闻发布会-中华人民共和国交通运输部",
            source_url=port_url,
        )

    snapshot["sourceSnapshots"].extend(
        [
            source_snapshot(
                source_id="open-meteo-air",
                release_id="open-meteo-no2-5city",
                title="Open-Meteo Air Quality API (China 5-city NO2 proxy)",
                date=end_date.isoformat(),
                url="https://air-quality-api.open-meteo.com/",
                summary="Alternative weekly/monthly NO2 proxy built from Beijing, Shanghai, Guangzhou, Shenzhen, and Chengdu.",
                highlights=[
                    snapshot["metrics"].get("Air pollution / NO2", {}).get("value", "n/a"),
                    snapshot["metrics"].get("Air pollution / NO2", {}).get("secondary", ""),
                ],
                tables=[],
            ),
            source_snapshot(
                source_id="eoatlas-nightlights",
                release_id="eoatlas-nightlights-china",
                title="Earth Observation Atlas monthly night lights (China)",
                date=latest_row["date"].date().isoformat(),
                url=night_url,
                summary="Monthly VIIRS-derived country-level night lights for China from the Earth Observation Atlas.",
                highlights=[
                    snapshot["metrics"].get("Night lights", {}).get("value", "n/a"),
                    snapshot["metrics"].get("Night lights", {}).get("secondary", ""),
                ],
                tables=[],
            ),
            source_snapshot(
                source_id="mot-home",
                release_id="mot-port-throughput-2025",
                title="2026年1月例行新闻发布会-中华人民共和国交通运输部",
                date="2026-01-30",
                url=port_url,
                summary="Ministry of Transport briefing with annual 2025 freight and port-throughput totals.",
                highlights=[
                    snapshot["metrics"].get("Port throughput", {}).get("value", "n/a"),
                    snapshot["metrics"].get("Port throughput", {}).get("secondary", ""),
                ],
                tables=[],
            ),
        ]
    )


def extract_nbs_means_of_production(snapshot: dict[str, Any]) -> None:
    url = "https://www.stats.gov.cn/english/PressRelease/202604/t20260403_1962984.html"
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True))
    date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
    table = read_tables_from_html(html)[0]

    def product_row(label: str) -> pd.Series | None:
        matches = table[table.iloc[:, 0].astype(str).str.contains(label, case=False, na=False)]
        if matches.empty:
            return None
        return matches.iloc[0]

    rebar = product_row("Rebar")
    copper = product_row("Electrolytic Copper")
    if rebar is not None:
        snapshot["metrics"]["Steel inventory / rebar prices"] = metric_entry(
            value=f"CNY {float(str(rebar.iloc[2]).replace(',', '')):,.1f}/ton",
            secondary=f"{rebar.iloc[3]} yuan vs prior period ({rebar.iloc[4]}%)",
            date=date,
            period="March 21-31 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
        )
    if rebar is not None or copper is not None:
        parts = []
        if rebar is not None:
            parts.append(f"Rebar CNY {float(str(rebar.iloc[2]).replace(',', '')):,.1f}/ton")
        if copper is not None:
            parts.append(f"Copper CNY {float(str(copper.iloc[2]).replace(',', '')):,.1f}/ton")
        snapshot["metrics"]["Commodity production and spot prices"] = metric_entry(
            value=" | ".join(parts),
            secondary="Latest monitored means-of-production prices in circulation",
            date=date,
            period="March 21-31 2026",
            source_id="nbs-releases",
            source_title=title,
            source_url=url,
    )


def build_composite_metrics(snapshot: dict[str, Any]) -> None:
    new_home = snapshot["metrics"].get("70-city new home price index")
    sales_area = snapshot["metrics"].get("Property sales by floor area")
    completions = snapshot["metrics"].get("Completions")
    urban_population = snapshot["metrics"].get("Urban permanent residents")

    if new_home and sales_area:
        snapshot["metrics"]["Home prices and housing turnover"] = metric_entry(
            value=f"{new_home['value']} | Sales {sales_area['value']}",
            secondary=f"{new_home.get('secondary', '')}; {sales_area.get('secondary', '')}",
            date=new_home["date"],
            period=new_home["period"],
            source_id=new_home["sourceId"],
            source_title=new_home["sourceTitle"],
            source_url=new_home["sourceUrl"],
        )

    if completions and urban_population:
        snapshot["metrics"]["Household formation proxies"] = metric_entry(
            value=f"Completions {completions['value']}",
            secondary=f"Urban permanent residents {urban_population['value']}",
            date=completions["date"],
            period=completions["period"],
            source_id=completions["sourceId"],
            source_title=completions["sourceTitle"],
            source_url=completions["sourceUrl"],
        )

    # Real interest rates: LPR minus CPI headline
    lpr_1y = snapshot["metrics"].get("1-year LPR")
    lpr_5y = snapshot["metrics"].get("5-year LPR")
    cpi = snapshot["metrics"].get("CPI headline")
    if lpr_1y and cpi:
        lpr_1y_val = parse_float(lpr_1y["value"])
        cpi_val = parse_float(cpi["value"])
        if lpr_1y_val is not None and cpi_val is not None:
            real_1y = lpr_1y_val - cpi_val
            snapshot["metrics"]["1Y real interest rate"] = metric_entry(
                value=f"{real_1y:+.2f}%",
                secondary=f"1Y LPR {lpr_1y_val:.2f}% minus CPI {cpi_val:.1f}%",
                date=max(lpr_1y["date"], cpi["date"]),
                period=cpi["period"],
                source_id="pboc-home",
                source_title="Computed: 1Y LPR minus CPI headline",
                source_url=lpr_1y.get("sourceUrl", ""),
            )
    if lpr_5y and cpi:
        lpr_5y_val = parse_float(lpr_5y["value"])
        cpi_val = parse_float(cpi["value"])
        if lpr_5y_val is not None and cpi_val is not None:
            real_5y = lpr_5y_val - cpi_val
            snapshot["metrics"]["5Y real interest rate"] = metric_entry(
                value=f"{real_5y:+.2f}%",
                secondary=f"5Y LPR {lpr_5y_val:.2f}% minus CPI {cpi_val:.1f}%",
                date=max(lpr_5y["date"], cpi["date"]),
                period=cpi["period"],
                source_id="pboc-home",
                source_title="Computed: 5Y LPR minus CPI headline",
                source_url=lpr_5y.get("sourceUrl", ""),
            )

    # Credit impulse: change in new credit flow as % of GDP
    tsf_flow = snapshot["metrics"].get("TSF flow")
    nominal_gdp_history = snapshot.get("history", {}).get("Nominal GDP growth", [])
    if tsf_flow and nominal_gdp_history:
        # Use the latest annual GDP level from history secondary field
        latest_gdp_entry = None
        for entry in sorted(nominal_gdp_history, key=lambda x: str(x.get("period", "")), reverse=True):
            gdp_tn_match = re.search(r"GDP RMB ([\d.]+) tn", entry.get("secondary", ""))
            if gdp_tn_match:
                latest_gdp_entry = float(gdp_tn_match.group(1))
                break
        if latest_gdp_entry and latest_gdp_entry > 0:
            tsf_val = parse_float(tsf_flow["value"])
            if tsf_val is not None:
                # TSF flow is in trillions; GDP is in trillions
                # Credit impulse ≈ TSF flow / GDP * 100 (annualized for monthly/bimonthly flow)
                impulse = (tsf_val / latest_gdp_entry) * 100
                snapshot["metrics"]["Credit impulse"] = metric_entry(
                    value=f"{impulse:.1f}% of GDP",
                    secondary=f"TSF flow {tsf_flow['value']} / annual GDP RMB {latest_gdp_entry:.1f} tn (approx; uses latest annual GDP as denominator)",
                    date=tsf_flow["date"],
                    period=tsf_flow["period"],
                    source_id="pboc-home",
                    source_title="Computed: TSF flow as share of GDP",
                    source_url=tsf_flow.get("sourceUrl", ""),
                )

    # --- New computed metrics ---

    # Real retail sales growth: nominal retail y/y minus CPI y/y
    retail = snapshot["metrics"].get("Retail sales")
    if retail and cpi:
        retail_secondary = retail.get("secondary", "")
        retail_val = parse_float(retail_secondary) if "% y/y" in retail_secondary else None
        cpi_val = parse_float(cpi["value"])
        if retail_val is not None and cpi_val is not None:
            real_retail = retail_val - cpi_val
            snapshot["metrics"]["Real retail sales growth"] = metric_entry(
                value=f"{real_retail:+.1f}% y/y",
                secondary=f"Nominal retail {retail_val:.1f}% minus CPI {cpi_val:.1f}%",
                date=retail["date"],
                period=retail["period"],
                source_id="computed",
                source_title="Computed: Retail sales growth minus CPI headline",
                source_url="",
            )

    # Real disposable income growth: nominal income y/y minus CPI y/y
    income = snapshot["metrics"].get("Per capita disposable income growth")
    if income and cpi:
        income_val = parse_float(income["value"])
        cpi_val = parse_float(cpi["value"])
        if income_val is not None and cpi_val is not None:
            real_income = income_val - cpi_val
            snapshot["metrics"]["Real disposable income growth"] = metric_entry(
                value=f"{real_income:+.1f}% y/y",
                secondary=f"Nominal income {income_val:.1f}% minus CPI {cpi_val:.1f}%",
                date=income["date"],
                period=income["period"],
                source_id="computed",
                source_title="Computed: Per capita disposable income growth minus CPI",
                source_url="",
            )

    # Real credit growth: TSF stock growth minus GDP deflator
    tsf_stock = snapshot["metrics"].get("TSF stock growth")
    gdp_deflator = snapshot["metrics"].get("GDP deflator")
    if tsf_stock and gdp_deflator:
        tsf_stock_val = parse_float(tsf_stock["value"])
        deflator_val = parse_float(gdp_deflator["value"])
        if tsf_stock_val is not None and deflator_val is not None:
            real_credit = tsf_stock_val - deflator_val
            snapshot["metrics"]["Real credit growth"] = metric_entry(
                value=f"{real_credit:+.1f}% y/y",
                secondary=f"TSF stock growth {tsf_stock_val:.1f}% minus GDP deflator {deflator_val:.1f}%",
                date=tsf_stock["date"],
                period=tsf_stock["period"],
                source_id="computed",
                source_title="Computed: TSF stock growth minus GDP deflator",
                source_url="",
            )

    # Current account as % of GDP
    ca = snapshot["metrics"].get("Current account")
    # Reuse latest_gdp_entry from credit impulse block if available
    if ca and nominal_gdp_history:
        if not locals().get("latest_gdp_entry"):
            latest_gdp_entry = None
            for entry in sorted(nominal_gdp_history, key=lambda x: str(x.get("period", "")), reverse=True):
                gdp_tn_match = re.search(r"GDP RMB ([\d.]+) tn", entry.get("secondary", ""))
                if gdp_tn_match:
                    latest_gdp_entry = float(gdp_tn_match.group(1))
                    break
        if latest_gdp_entry and latest_gdp_entry > 0:
            ca_match = re.search(r"([\d.]+)\s*bn", ca["value"])
            usdcny = snapshot["metrics"].get("USD/CNY")
            fx_rate = parse_float(usdcny["value"]) if usdcny else 7.2
            if ca_match and fx_rate and fx_rate > 0:
                ca_usd_bn = float(ca_match.group(1))
                gdp_usd_tn = latest_gdp_entry / fx_rate
                ca_pct = (ca_usd_bn / 1000) / gdp_usd_tn * 100
                snapshot["metrics"]["Current account as % of GDP"] = metric_entry(
                    value=f"{ca_pct:+.1f}% of GDP",
                    secondary=f"CA +USD {ca_usd_bn:.1f} bn / GDP ~USD {gdp_usd_tn:.1f} tn (at {fx_rate:.2f})",
                    date=ca["date"],
                    period=ca["period"],
                    source_id="computed",
                    source_title="Computed: Current account surplus as share of GDP",
                    source_url="",
                )

    # Fiscal impulse: broad fiscal deficit as % of GDP
    broad_deficit = snapshot["metrics"].get("Broad fiscal deficit")
    if broad_deficit and nominal_gdp_history:
        if not locals().get("latest_gdp_entry"):
            latest_gdp_entry = None
            for entry in sorted(nominal_gdp_history, key=lambda x: str(x.get("period", "")), reverse=True):
                gdp_tn_match = re.search(r"GDP RMB ([\d.]+) tn", entry.get("secondary", ""))
                if gdp_tn_match:
                    latest_gdp_entry = float(gdp_tn_match.group(1))
                    break
        deficit_val = parse_float(broad_deficit["value"])
        if deficit_val is not None and latest_gdp_entry and latest_gdp_entry > 0:
            deficit_pct = (deficit_val / latest_gdp_entry) * 100
            snapshot["metrics"]["Fiscal impulse"] = metric_entry(
                value=f"{deficit_pct:.1f}% of GDP",
                secondary=f"Broad fiscal deficit RMB {deficit_val:.2f} tn / GDP RMB {latest_gdp_entry:.1f} tn (single-period ratio; delta requires prior period)",
                date=broad_deficit["date"],
                period=broad_deficit["period"],
                source_id="computed",
                source_title="Computed: Broad fiscal deficit as share of GDP",
                source_url="",
            )

    # Momentum fields for key metrics
    _add_momentum_fields(snapshot)


def _add_momentum_fields(snapshot: dict[str, Any]) -> None:
    """For key metrics with history, compare current vs prior y/y rate to show acceleration/deceleration."""
    momentum_targets = [
        "Retail sales",
        "Property sales by floor area",
        "Industrial production",
        "Exports (goods, RMB)",
        "Imports (goods, RMB)",
        "CPI headline",
        "PPI",
        "Industrial profits",
        "Real retail sales growth",
        "Housing starts",
        "Completions",
    ]
    for name in momentum_targets:
        history = snapshot.get("history", {}).get(name, [])
        if len(history) < 2:
            continue
        sorted_h = sorted(history, key=lambda x: str(x.get("period", "")), reverse=True)
        current = sorted_h[0]
        previous = sorted_h[1]
        if current.get("numeric") is not None and previous.get("numeric") is not None:
            delta = current["numeric"] - previous["numeric"]
            if delta > 0.1:
                direction = "accelerating"
            elif delta < -0.1:
                direction = "decelerating"
            else:
                direction = "stable"
            metric = snapshot["metrics"].get(name)
            if metric:
                metric["momentum"] = {
                    "current": current["value"],
                    "previous": previous["value"],
                    "delta": f"{delta:+.1f} pp",
                    "direction": direction,
                }


def extract_policy_context(snapshot: dict[str, Any]) -> None:
    # Fetch latest PBOC speech from the speeches index
    speech_url = "https://www.pbc.gov.cn/en/3688110/3688175/2026032317344948259/index.html"
    fallback_url = "https://www.pbc.gov.cn/en/3688110/3688175/2025080817533640398/index.html"
    url = speech_url
    try:
        html = fetch(url).text
        soup = soup_from_html(html)
        title = clean_text(
            soup.find("meta", attrs={"name": "ArticleTitle"})["content"]
            if soup.find("meta", attrs={"name": "ArticleTitle"})
            else soup.title.get_text(" ", strip=True)
        )
        date = clean_text(
            soup.find("meta", attrs={"name": "PubDate"})["content"]
            if soup.find("meta", attrs={"name": "PubDate"})
            else "2026-03-22"
        )
        summary = clean_text(
            soup.find("meta", attrs={"name": "Description"})["content"]
            if soup.find("meta", attrs={"name": "Description"})
            else "Latest accessible policy-language page wired into the dashboard."
        )
        text = clean_text(article_text(soup))
        # Extract current policy stance language
        stance_match = re.search(
            r"((?:supportive|moderately loose|prudent|accommodative)\s+monetary\s+policy\s+stance)",
            text,
            re.I,
        )
        stance_phrase = stance_match.group(1) if stance_match else "supportive monetary policy stance"
    except Exception:
        url = fallback_url
        title = "PBOC policy-language page status"
        date = datetime.now().date().isoformat()
        summary = "Policy-language feed is configured, but this refresh used a fallback status snapshot."
        stance_phrase = "supportive monetary policy stance"

    add_status_snapshot(
        snapshot,
        source_id="pboc-policy",
        release_id="pboc-policy-language-status",
        title=title,
        date=date,
        url=url,
        summary=summary,
        highlights=[
            "Use this source family for policy wording shifts and signal changes before the hard data moves.",
            "City-level housing easing still requires municipal-government or local-financial-media parsing.",
        ],
    )
    snapshot["metrics"]["Politburo and State Council wording changes"] = metric_entry(
        value=f'Current stance: "{stance_phrase}"',
        secondary='Property package continues to be framed around "four cancellations, four reductions, two increases"',
        date=date,
        period=date,
        source_id="pboc-policy",
        source_title=title,
        source_url=url,
    )
    snapshot["metrics"]["Major-city mortgage and purchase restriction changes"] = metric_entry(
        value="Shanghai cut first-home down payment to 15%",
        secondary="Official city easing summaries also highlighted Shenzhen non-core-area purchase relaxation and lower qualification thresholds",
        date="2025-01-25",
        period="2024-2025 easing wave",
        source_id="pboc-policy",
        source_title="Official city housing-policy easing summaries",
        source_url="https://www.shanghai.gov.cn/cmsres/5d/5d302c315a9d4a09ba2bbf78161e6756/2e1e3dfdb0860d9e3f79c810eb95f833.pdf",
    )
    snapshot["sourceSnapshots"].append(
        source_snapshot(
            source_id="pboc-policy",
            release_id="city-policy-easing-summary",
            title="Official city housing-policy easing summaries",
            date="2025-01-25",
            url="https://www.shanghai.gov.cn/cmsres/5d/5d302c315a9d4a09ba2bbf78161e6756/2e1e3dfdb0860d9e3f79c810eb95f833.pdf",
            summary="City-level housing policy tracker anchored on official Shanghai policy measures and the broader major-city easing wave.",
            highlights=[
                snapshot["metrics"]["Politburo and State Council wording changes"]["value"],
                snapshot["metrics"]["Major-city mortgage and purchase restriction changes"]["value"],
            ],
            tables=[],
        )
    )


def extract_aux_source_status(snapshot: dict[str, Any]) -> None:
    today = datetime.now().date().isoformat()
    add_status_snapshot(
        snapshot,
        source_id="sse-scfi",
        release_id="scfi-feed-status",
        title="SCFI feed status",
        date=today,
        url="https://en.sse.net.cn/",
        summary="The Shanghai Shipping Exchange source family is configured, but a stable public historical SCFI parser is not yet wired into this refresh.",
        highlights=[
            "Shipping-rate metrics remain on the cycle map with the source family attached.",
            "A follow-up pass can bind the public SCFI release format directly into the dashboard.",
        ],
    )


def probe_customs(snapshot: dict[str, Any]) -> None:
    url = "https://english.customs.gov.cn/Statistics/Statistics?ColumnId=1"
    try:
        response = SESSION.get(url, timeout=(10, 60), verify=False)
        if response.status_code != 200:
            message = (
                f"GACC English statistics index returned HTTP {response.status_code} on "
                f"{datetime.now().date().isoformat()}, so the dashboard is using CEIC pages "
                "that attribute the underlying series to the General Administration of Customs "
                "for commodity detail and tech-trade metrics."
            )
            snapshot["notes"].append(message)
            add_status_snapshot(
                snapshot,
                source_id="gacc-stats",
                release_id="gacc-trade-feed-status",
                title="GACC trade feed status",
                date=datetime.now().date().isoformat(),
                url=url,
                summary=message,
                highlights=[
                    "Headline goods trade values on the page currently come from the NBS activity release.",
                    "Commodity detail and tech-trade metrics are filled from CEIC pages reported by GACC.",
                ],
            )
            add_status_snapshot(
                snapshot,
                source_id="gacc-major",
                release_id="gacc-major-feed-status",
                title="GACC commodity and partner-detail feed status",
                date=datetime.now().date().isoformat(),
                url="https://english.customs.gov.cn/Statistics/Statistics?ColumnId=6",
                summary="The GACC English statistics index is unavailable, so detail metrics are sourced from CEIC pages that cite GACC as the reporter.",
                highlights=[
                    "Commodity and partner-detail metrics are filled on-page despite the GACC English index failure.",
                    "A follow-up parser can still target the direct customs article pages for a cleaner official path.",
                ],
            )
        else:
            snapshot["notes"].append(
                "GACC English statistics index responded successfully, but headline trade values are currently sourced from the NBS activity release."
            )
            add_status_snapshot(
                snapshot,
                source_id="gacc-stats",
                release_id="gacc-trade-feed-status",
                title="GACC trade feed status",
                date=datetime.now().date().isoformat(),
                url=url,
                summary="GACC responded during refresh, but the current page still uses the NBS headline trade release for top-line values.",
                highlights=[
                    "Direct customs detail parsing is the next extension point for destination and commodity data.",
                ],
            )
    except Exception as exc:
        message = f"GACC English statistics index could not be fetched during refresh: {type(exc).__name__}: {exc}"
        snapshot["notes"].append(message)
        add_status_snapshot(
            snapshot,
            source_id="gacc-stats",
            release_id="gacc-trade-feed-status",
            title="GACC trade feed status",
            date=datetime.now().date().isoformat(),
            url=url,
            summary=message,
            highlights=[
                "Headline goods trade values on the page currently come from the NBS activity release.",
            ],
        )
        add_status_snapshot(
            snapshot,
            source_id="gacc-major",
            release_id="gacc-major-feed-status",
            title="GACC commodity and partner-detail feed status",
            date=datetime.now().date().isoformat(),
            url="https://english.customs.gov.cn/Statistics/Statistics?ColumnId=6",
            summary="Commodity and partner-detail parsing is blocked in this refresh because the GACC English statistics entry point did not respond cleanly.",
            highlights=[
                "Destination and commodity metrics remain visible on the page with feed-status context.",
            ],
        )


def build_pmi_history(snapshot: dict[str, Any]) -> None:
    url = "https://www.stats.gov.cn/english/PressRelease/202604/t20260401_1962920.html"
    html = fetch(url).text
    soup = soup_from_html(html)
    title = clean_text(soup.title.get_text(" ", strip=True))
    tables = read_tables_from_html(html)

    related_rows: dict[str, pd.Series] = {}
    current_year: int | None = None
    for _, row in tables[1].iloc[2:].iterrows():
        iso_date, current_year = month_label_to_iso(row.iloc[0], current_year)
        related_rows[iso_date] = row

    nonmfg_rows: dict[str, pd.Series] = {}
    current_year = None
    for _, row in tables[2].iloc[2:].iterrows():
        iso_date, current_year = month_label_to_iso(row.iloc[0], current_year)
        nonmfg_rows[iso_date] = row

    current_year = None
    for _, row in tables[0].iloc[3:].iterrows():
        iso_date, current_year = month_label_to_iso(row.iloc[0], current_year)
        related = related_rows.get(iso_date)
        nonmfg = nonmfg_rows.get(iso_date)
        period = iso_date[:7]

        pmi_points = [
            ("Official manufacturing PMI", f"{row.iloc[1]}", float(row.iloc[1]), ""),
            ("PMI output", f"{row.iloc[2]}", float(row.iloc[2]), ""),
            ("PMI new orders", f"{row.iloc[3]}", float(row.iloc[3]), ""),
            ("PMI raw-material inventory", f"{row.iloc[4]}", float(row.iloc[4]), ""),
        ]
        if related is not None:
            pmi_points.extend(
                [
                    ("PMI export orders", f"{related.iloc[1]}", float(related.iloc[1]), ""),
                    ("PMI input prices", f"{related.iloc[4]}", float(related.iloc[4]), ""),
                    ("PMI output prices", f"{related.iloc[5]}", float(related.iloc[5]), ""),
                    ("PMI finished-goods inventory", f"{related.iloc[6]}", float(related.iloc[6]), ""),
                ]
            )
        if nonmfg is not None:
            pmi_points.append(
                (
                    "PMI employment sub-indices",
                    f"Manufacturing {row.iloc[5]} | Non-manufacturing {nonmfg.iloc[5]}",
                    float(row.iloc[5]),
                    "Numeric series uses manufacturing employment index",
                )
            )

        for metric_name, value, numeric, secondary in pmi_points:
            add_history_point(
                snapshot,
                metric_name=metric_name,
                value=value,
                numeric=numeric,
                date=iso_date,
                period=period,
                source_id="nbs-pmi",
                source_title=title,
                source_url=url,
                secondary=secondary or "Monthly series from NBS PMI table",
            )


def build_nbs_archive_history(snapshot: dict[str, Any]) -> None:
    releases = crawl_nbs_press_releases()

    def add_metric_history_from_entry(
        metric_name: str,
        entry: dict[str, str],
        *,
        numeric: float | None = None,
    ) -> None:
        add_history_point(
            snapshot,
            metric_name=metric_name,
            value=entry["value"],
            numeric=numeric,
            date=entry["date"],
            period=entry["period"],
            source_id=entry["sourceId"],
            source_title=entry["sourceTitle"],
            source_url=entry["sourceUrl"],
            secondary=entry.get("secondary", ""),
        )

    for item in select_nbs_releases(releases, title_fragment="Sales Prices of Commercial Residential Buildings", limit=12):
        try:
            html = fetch(item["url"]).text
            soup = soup_from_html(html)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
            tables = read_tables_from_html(html)

            def parse_city_table(df: pd.DataFrame) -> list[dict[str, float]]:
                rows = []
                for idx in range(2, len(df)):
                    values = [stringify(value) for value in df.iloc[idx].tolist()]
                    for offset in (0, 3):
                        city = values[offset]
                        if not city or city.lower().startswith("note"):
                            continue
                        rows.append({"mom": float(values[offset + 1]), "yoy": float(values[offset + 2])})
                return rows

            new_rows = parse_city_table(tables[0])
            existing_rows = parse_city_table(tables[1])
            period = period_from_title(title)
            add_history_point(
                snapshot,
                metric_name="70-city new home price index",
                value=f"Avg M/M {sum(item['mom'] for item in new_rows) / len(new_rows):.2f}",
                numeric=sum(item["mom"] for item in new_rows) / len(new_rows),
                date=date,
                period=period,
                source_id="nbs-70city",
                source_title=title,
                source_url=item["url"],
                secondary=f"Avg Y/Y {sum(item['yoy'] for item in new_rows) / len(new_rows):.2f}",
            )
            add_history_point(
                snapshot,
                metric_name="70-city existing home price index",
                value=f"Avg M/M {sum(item['mom'] for item in existing_rows) / len(existing_rows):.2f}",
                numeric=sum(item["mom"] for item in existing_rows) / len(existing_rows),
                date=date,
                period=period,
                source_id="nbs-70city",
                source_title=title,
                source_url=item["url"],
                secondary=f"Avg Y/Y {sum(item['yoy'] for item in existing_rows) / len(existing_rows):.2f}",
            )
        except Exception:
            continue

    for item in select_nbs_releases(releases, title_fragment="Investment in Real Estate Development", limit=12):
        try:
            html = fetch(item["url"]).text
            soup = soup_from_html(html)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
            rows = row_lookup(read_tables_from_html(html)[0])
            period = period_from_title(title)
            mapping = {
                "Real estate investment": "Investment in real estate development (100 million yuan)",
                "Property sales by floor area": "Floor space of newly built commercial buildings sold (10,000 sq.m)",
                "Property sales by value": "Sales of newly built commercial buildings (100 million yuan)",
                "Housing starts": "Floor space of buildings newly started (10,000 sq.m)",
                "Construction under way": "Floor space of buildings under construction (10,000 sq.m)",
                "Completions": "Floor space of buildings completed (10,000 sq.m)",
                "Funds available to developers": "Funds for investment this year for real estate development enterprises (100 million yuan)",
            }
            formatters = {
                "Real estate investment": from_100m_yuan,
                "Property sales by floor area": from_10k_sqm,
                "Property sales by value": from_100m_yuan,
                "Housing starts": from_10k_sqm,
                "Construction under way": from_10k_sqm,
                "Completions": from_10k_sqm,
                "Funds available to developers": from_100m_yuan,
            }
            for metric_name, label in mapping.items():
                row = rows.get(label)
                if not row:
                    continue
                add_history_point(
                    snapshot,
                    metric_name=metric_name,
                    value=formatters[metric_name](row["c1"]),
                    numeric=parse_float(row["c2"]),
                    date=date,
                    period=period,
                    source_id="nbs-releases",
                    source_title=title,
                    source_url=item["url"],
                    secondary=f"{row['c2']}% y/y",
                )
        except Exception:
            continue

    for item in select_nbs_releases(releases, title_fragment="Investment in Fixed Assets", limit=12):
        try:
            html = fetch(item["url"]).text
            soup = soup_from_html(html)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
            text = article_text(soup)
            rows = row_lookup(read_tables_from_html(html)[0])
            period = period_from_title(title)
            manufacturing = rows.get("Manufacturing")
            if manufacturing:
                add_history_point(
                    snapshot,
                    metric_name="Manufacturing fixed-asset investment",
                    value=f"{manufacturing['c1']}% y/y",
                    numeric=parse_float(manufacturing["c1"]),
                    date=date,
                    period=period,
                    source_id="nbs-releases",
                    source_title=title,
                    source_url=item["url"],
                    secondary="Manufacturing FAI growth",
                )
            infra_match = re.search(r"investment in infrastructure .*? increased by ([\d.]+)%", text, re.I)
            if infra_match:
                add_history_point(
                    snapshot,
                    metric_name="Infrastructure fixed-asset investment",
                    value=f"{infra_match.group(1)}% y/y",
                    numeric=float(infra_match.group(1)),
                    date=date,
                    period=period,
                    source_id="nbs-releases",
                    source_title=title,
                    source_url=item["url"],
                    secondary="Infrastructure FAI growth",
                )
        except Exception:
            continue

    for item in select_nbs_releases(releases, title_fragment="Industrial Production Operation", limit=12):
        try:
            html = fetch(item["url"]).text
            soup = soup_from_html(html)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
            period = period_from_title(title)
            rows = row_lookup(read_tables_from_html(html)[0])
            headline = rows.get("Value Added of Industrial Enterprises Above the Designated Size")
            if headline:
                add_history_point(
                    snapshot,
                    metric_name="Industrial production",
                    value=f"{headline['c2']}% y/y",
                    numeric=parse_float(headline["c2"]),
                    date=date,
                    period=period,
                    source_id="nbs-releases",
                    source_title=title,
                    source_url=item["url"],
                    secondary="Value added growth",
                )
        except Exception:
            continue

    for item in select_nbs_releases(releases, title_fragment="Total Retail Sales of Consumer Goods", limit=12):
        try:
            html = fetch(item["url"]).text
            soup = soup_from_html(html)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
            period = period_from_title(title)
            rows = row_lookup(read_tables_from_html(html)[0])
            retail_map = {
                "Retail sales": "Total retail sales of consumer goods",
                "Retail sales ex-autos": "Of which: Retail sales of consumer goods excluding automobiles",
                "Online retail sales": "Of which: Online retail sales of goods",
                "Catering revenue": "Income of the catering industry",
            }
            for metric_name, label in retail_map.items():
                row = rows.get(label)
                if not row:
                    continue
                add_history_point(
                    snapshot,
                    metric_name=metric_name,
                    value=from_100m_yuan(row["c1"]),
                    numeric=parse_float(row["c2"]),
                    date=date,
                    period=period,
                    source_id="nbs-releases",
                    source_title=title,
                    source_url=item["url"],
                    secondary=f"{row['c2']}% y/y",
                )
        except Exception:
            continue

    for item in select_nbs_releases(releases, title_fragment="Consumer Price Index in", limit=12):
        try:
            html = fetch(item["url"]).text
            soup = soup_from_html(html)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
            period = period_from_title(title)
            rows = row_lookup(read_tables_from_html(html)[0])
            cpi_map = {
                "CPI headline": "Consumer Price Index",
                "Food CPI": "Of which: Food",
                "Services CPI": "Services",
                "Core CPI": "Of which: Excluding food and energy",
            }
            for metric_name, label in cpi_map.items():
                row = rows.get(label)
                if not row:
                    continue
                add_history_point(
                    snapshot,
                    metric_name=metric_name,
                    value=f"{row['c2']}% y/y",
                    numeric=parse_float(row["c2"]),
                    date=date,
                    period=period,
                    source_id="nbs-cpi",
                    source_title=title,
                    source_url=item["url"],
                    secondary=f"{row['c1']}% m/m",
                )
        except Exception:
            continue

    for item in select_nbs_releases(releases, title_fragment="Industrial Producer Price Indexes in", limit=12):
        try:
            html = fetch(item["url"]).text
            soup = soup_from_html(html)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
            period = period_from_title(title)
            rows = row_lookup(read_tables_from_html(html)[0])
            row = rows.get("I. Producer Price Indexes for Industrial Products")
            if not row:
                continue
            add_history_point(
                snapshot,
                metric_name="PPI",
                value=f"{row['c2']}% y/y",
                numeric=parse_float(row["c2"]),
                date=date,
                period=period,
                source_id="nbs-cpi",
                source_title=title,
                source_url=item["url"],
                secondary=f"{row['c1']}% m/m",
            )
        except Exception:
            continue

    for item in select_nbs_releases(releases, title_fragment="National Economy", limit=12):
        try:
            html = fetch(item["url"]).text
            soup = soup_from_html(html)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = clean_text(soup.find("meta", attrs={"name": "PubDate"})["content"])
            period = period_from_title(title)
            text = article_text(soup)
            trade_match = re.search(
                (
                    r"value of exports was ([\d,.]+) billion yuan, up by ([\d.]+) percent, and the value of imports was "
                    r"([\d,.]+) billion yuan, up by ([\d.]+) percent"
                ),
                text,
                re.I,
            )
            unemployment_match = re.search(
                r"urban surveyed unemployment rate was ([\d.]+) percent.*?31 major cities was ([\d.]+) percent.*?worked ([\d.]+) hours per week on average",
                text,
                re.I,
            )
            service_match = re.search(
                r"Index of Services Production grew by ([\d.]+) percent year on year",
                text,
                re.I,
            )
            if trade_match:
                exports, export_growth, imports, import_growth = trade_match.groups()
                trade_balance = float(exports.replace(",", "")) - float(imports.replace(",", ""))
                add_history_point(
                    snapshot,
                    metric_name="Exports (goods, RMB)",
                    value=format_billion_yuan(float(exports.replace(",", ""))),
                    numeric=float(export_growth),
                    date=date,
                    period=period,
                    source_id="nbs-releases",
                    source_title=title,
                    source_url=item["url"],
                    secondary=f"{export_growth}% y/y",
                )
                add_history_point(
                    snapshot,
                    metric_name="Imports (goods, RMB)",
                    value=format_billion_yuan(float(imports.replace(",", ""))),
                    numeric=float(import_growth),
                    date=date,
                    period=period,
                    source_id="nbs-releases",
                    source_title=title,
                    source_url=item["url"],
                    secondary=f"{import_growth}% y/y",
                )
                add_history_point(
                    snapshot,
                    metric_name="Trade balance",
                    value=format_billion_yuan(trade_balance),
                    numeric=trade_balance,
                    date=date,
                    period=period,
                    source_id="nbs-releases",
                    source_title=title,
                    source_url=item["url"],
                    secondary="Goods trade balance, CNY terms",
                )
            if unemployment_match:
                urban, city31, hours = unemployment_match.groups()
                add_history_point(
                    snapshot,
                    metric_name="Urban surveyed unemployment",
                    value=f"{urban}%",
                    numeric=float(urban),
                    date=date,
                    period=period,
                    source_id="nbs-releases",
                    source_title=title,
                    source_url=item["url"],
                    secondary="Monthly surveyed rate",
                )
                add_history_point(
                    snapshot,
                    metric_name="31-city unemployment",
                    value=f"{city31}%",
                    numeric=float(city31),
                    date=date,
                    period=period,
                    source_id="nbs-releases",
                    source_title=title,
                    source_url=item["url"],
                    secondary="31-city surveyed rate",
                )
                add_history_point(
                    snapshot,
                    metric_name="Hours worked per week",
                    value=f"{hours} hours/week",
                    numeric=float(hours),
                    date=date,
                    period=period,
                    source_id="nbs-releases",
                    source_title=title,
                    source_url=item["url"],
                    secondary="Enterprise employees average",
                )
            if service_match:
                add_history_point(
                    snapshot,
                    metric_name="Service-sector activity",
                    value=f"{service_match.group(1)}% y/y",
                    numeric=float(service_match.group(1)),
                    date=date,
                    period=period,
                    source_id="nbs-releases",
                    source_title=title,
                    source_url=item["url"],
                    secondary="Index of Services Production",
                )
        except Exception:
            continue


def build_structural_history(snapshot: dict[str, Any]) -> None:
    items = [
        (
            "https://www.stats.gov.cn/english/PressRelease/202602/t20260228_1962661.html",
            "2025",
        ),
        (
            "https://www.stats.gov.cn/english/PressRelease/202502/t20250228_1958822.html",
            "2024",
        ),
        (
            "https://www.stats.gov.cn/english/PressRelease/202402/t20240228_1947918.html",
            "2023",
        ),
        (
            "https://www.stats.gov.cn/english/PressRelease/202302/t20230227_1918979.html",
            "2022",
        ),
        (
            "https://www.stats.gov.cn/english/PressRelease/202202/t20220227_1827963.html",
            "2021",
        ),
    ]
    annual_stats: list[dict[str, float | str]] = []
    for url, period in items:
        try:
            html = fetch(url).text
            soup = soup_from_html(html)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = page_pub_date(soup, url)
            text = article_text(soup)
            pop_tables = read_tables_from_html(html)
            population = row_lookup(pop_tables[0])
            urban_row = row_lookup_contains(population, "Of which: Urban")
            total_row = population.get("National Total")
            working_age_row = row_lookup_contains(population, "Aged 16-59")
            age_0_15_row = row_lookup_contains(population, "Aged 0-15")
            age_60_row = row_lookup_contains(population, "Aged 60 and above")
            age_65_row = row_lookup_contains(population, "Aged 65 and above")
            birth_match = re.search(
                r"There were ([\d.]+) million births.*?there were ([\d.]+) million deaths.*?natural growth rate was (-?[\d.]+) per thousand",
                text,
                re.I,
            )
            gdp_match = re.search(
                r"gross domestic product .*? in \d{4} was ([\d,.]+) billion yuan, (?:up by|an increase of) ([\d.]+) percent",
                text,
                re.I,
            )
            income_match = re.search(
                r"per capita disposable income nationwide was [\d,]+ yuan, an increase of ([\d.]+) percent",
                text,
                re.I,
            )
            high_tech_investment_match = re.search(
                r"investment in high technology industr(?:y|ies).*? increased by ([\d.]+) percent.*?technology transformation of manufacturing.*? grew by ([\d.]+) percent",
                text,
                re.I,
            )
            migrant_match = first_match(
                text,
                [
                    r"total number of migrant workers[^.]*?was ([\d.]+) million, up by ([\d.]+) percent",
                    r"migrant workers[^.]*?was ([\d.]+) million, up by ([\d.]+) percent",
                ],
            )
            nev_match = first_match(
                text,
                [
                    r"output of new energy vehicles reached ([\d.]+) million, up by ([\d.]+) percent",
                    r"output of new energy vehicles was ([\d.]+) million, up by ([\d.]+) percent",
                ],
            )
            integrated_circuit_row = find_row_in_tables(
                pop_tables,
                "Integrated circuits",
                unit_contains="pieces",
            )
            solar_cell_row = find_row_in_tables(pop_tables, "Solar cells")
            mobile_phone_row = find_row_in_tables(pop_tables, "Mobile telephones")
            rail_freight_row = find_row_in_tables(pop_tables, "Railways", unit_contains="100 million tons")
            freight_flow_row = find_row_in_tables(
                pop_tables,
                "Freight flows",
                unit_contains="100 million ton-kilometers",
            )
            port_match = first_match(
                text,
                [
                    r"port cargo throughput was ([\d.]+) billion tons, up by ([\d.]+) percent",
                    r"cargo throughput of ports was ([\d.]+) billion tons, up by ([\d.]+) percent",
                    r"the cargo throughput of ports was ([\d.]+) billion tons, up by ([\d.]+) percent",
                ],
            )
            if total_row:
                add_history_point(
                    snapshot,
                    metric_name="Total population",
                    value=f"{float(total_row['c1']) / 10000:.3f} bn",
                    numeric=float(total_row["c1"]) / 10000,
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary="Year-end population",
                )
            if urban_row:
                add_history_point(
                    snapshot,
                    metric_name="Urbanization rate",
                    value=f"{urban_row['c2']}%",
                    numeric=parse_float(urban_row["c2"]),
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary="Urban share of population",
                )
                add_history_point(
                    snapshot,
                    metric_name="Urban permanent residents",
                    value=f"{float(urban_row['c1']) / 10000:.3f} bn",
                    numeric=float(urban_row["c1"]) / 10000,
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary=f"{urban_row['c2']}% of total population",
                )
            if working_age_row:
                add_history_point(
                    snapshot,
                    metric_name="Working-age population share",
                    value=f"{working_age_row['c2']}%",
                    numeric=parse_float(working_age_row["c2"]),
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary="Aged 16-59",
                )
            if age_0_15_row and age_60_row and age_65_row:
                age_65_numeric = parse_float(age_65_row["c2"])
                add_history_point(
                    snapshot,
                    metric_name="Age structure",
                    value=(
                        f"0-15: {age_0_15_row['c2']}% | "
                        f"60+: {age_60_row['c2']}% | "
                        f"65+: {age_65_row['c2']}%"
                    ),
                    numeric=age_65_numeric if age_65_numeric is not None else parse_float(age_60_row["c2"]),
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary="Annual population age mix",
                )
            if birth_match:
                births, deaths, natural_growth = birth_match.groups()
                add_history_point(
                    snapshot,
                    metric_name="Births",
                    value=f"{births} mn",
                    numeric=float(births),
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary="Annual births",
                )
                add_history_point(
                    snapshot,
                    metric_name="Deaths",
                    value=f"{deaths} mn",
                    numeric=float(deaths),
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary="Annual deaths",
                )
                add_history_point(
                    snapshot,
                    metric_name="Natural population growth",
                    value=f"{natural_growth} per thousand",
                    numeric=float(natural_growth),
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary="Annual natural growth",
                )
            if migrant_match:
                migrant_workers, growth = migrant_match.groups()
                for metric_name in ("Migrant worker population", "Migrant worker totals"):
                    add_history_point(
                        snapshot,
                        metric_name=metric_name,
                        value=f"{migrant_workers} mn",
                        numeric=float(migrant_workers),
                        date=date,
                        period=period,
                        source_id="nbs-communique",
                        source_title=title,
                        source_url=url,
                        secondary=f"{growth}% y/y",
                    )
            if integrated_circuit_row:
                integrated_output = parse_float(integrated_circuit_row["value"])
                add_history_point(
                    snapshot,
                    metric_name="Integrated-circuit output",
                    value=f"{integrated_circuit_row['value']} ({integrated_circuit_row['unit']})",
                    numeric=integrated_output,
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary=f"{integrated_circuit_row['change']}% y/y",
                )
            if solar_cell_row:
                solar_output = parse_float(solar_cell_row["value"])
                add_history_point(
                    snapshot,
                    metric_name="Solar-cell output",
                    value=f"{solar_cell_row['value']} ({solar_cell_row['unit']})",
                    numeric=solar_output,
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary=f"{solar_cell_row['change']}% y/y",
                )
            if mobile_phone_row:
                mobile_output = parse_float(mobile_phone_row["value"])
                add_history_point(
                    snapshot,
                    metric_name="Mobile telephones",
                    value=f"{mobile_phone_row['value']} ({mobile_phone_row['unit']})",
                    numeric=mobile_output,
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary=f"{mobile_phone_row['change']}% y/y",
                )
            if nev_match:
                nev_output, nev_growth = nev_match.groups()
                add_history_point(
                    snapshot,
                    metric_name="EV output",
                    value=f"{nev_output} mn units",
                    numeric=float(nev_output),
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary=f"+{nev_growth}% y/y",
                )
            if rail_freight_row:
                rail_value = parse_float(rail_freight_row["value"])
                add_history_point(
                    snapshot,
                    metric_name="Rail freight",
                    value=f"{rail_freight_row['value']} {rail_freight_row['unit']}",
                    numeric=rail_value,
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary=f"{rail_freight_row['change']}% y/y",
                )
            if freight_flow_row:
                freight_value = parse_float(freight_flow_row["value"])
                add_history_point(
                    snapshot,
                    metric_name="Freight traffic / ton-kilometers",
                    value=f"{freight_flow_row['value']} {freight_flow_row['unit']}",
                    numeric=freight_value,
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary=f"{freight_flow_row['change']}% y/y",
                )
            if port_match:
                port_tonnage, port_growth = port_match.groups()
                add_history_point(
                    snapshot,
                    metric_name="Port throughput",
                    value=f"{float(port_tonnage):.1f} bn tons",
                    numeric=float(port_tonnage),
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary=f"{float(port_growth):.1f}% y/y",
                )
            if high_tech_investment_match:
                high_tech_growth, tech_transform_growth = high_tech_investment_match.groups()
                add_history_point(
                    snapshot,
                    metric_name="High-tech industry investment",
                    value=f"{high_tech_growth}% y/y",
                    numeric=float(high_tech_growth),
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary="Annual high-technology industry investment growth",
                )
                add_history_point(
                    snapshot,
                    metric_name="Technology-transformation investment",
                    value=f"{tech_transform_growth}% y/y",
                    numeric=float(tech_transform_growth),
                    date=date,
                    period=period,
                    source_id="nbs-communique",
                    source_title=title,
                    source_url=url,
                    secondary="Annual manufacturing technology-transformation investment growth",
                )
            if gdp_match:
                gdp_value, real_growth = gdp_match.groups()
                annual_stats.append(
                    {
                        "period": period,
                        "date": date,
                        "gdp": float(gdp_value.replace(",", "")),
                        "real_growth": float(real_growth),
                        "income_growth": float(income_match.group(1)) if income_match else None,
                        "title": title,
                        "url": url,
                    }
                )
        except Exception:
            continue

    annual_stats.sort(key=lambda item: str(item["period"]))
    for previous, current in zip(annual_stats, annual_stats[1:]):
        nominal_growth = ((float(current["gdp"]) / float(previous["gdp"])) - 1) * 100
        real_growth = float(current["real_growth"])
        gdp_deflator = (((1 + nominal_growth / 100) / (1 + real_growth / 100)) - 1) * 100
        add_history_point(
            snapshot,
            metric_name="Nominal GDP growth",
            value=f"{nominal_growth:.1f}% y/y",
            numeric=nominal_growth,
            date=str(current["date"]),
            period=str(current["period"]),
            source_id="nbs-releases",
            source_title=str(current["title"]),
            source_url=str(current["url"]),
            secondary=f"GDP RMB {float(current['gdp']) / 1000:.2f} tn",
        )
        add_history_point(
            snapshot,
            metric_name="GDP deflator",
            value=f"{gdp_deflator:.1f}%",
            numeric=gdp_deflator,
            date=str(current["date"]),
            period=str(current["period"]),
            source_id="nbs-releases",
            source_title=str(current["title"]),
            source_url=str(current["url"]),
            secondary=f"Real GDP growth {real_growth:.1f}%",
        )
        add_history_point(
            snapshot,
            metric_name="Real GDP growth",
            value=f"{real_growth:.1f}% y/y",
            numeric=real_growth,
            date=str(current["date"]),
            period=str(current["period"]),
            source_id="nbs-releases",
            source_title=str(current["title"]),
            source_url=str(current["url"]),
            secondary=f"Nominal GDP growth {nominal_growth:.1f}%; GDP deflator {gdp_deflator:.1f}%",
        )
        if current.get("income_growth") is not None:
            add_history_point(
                snapshot,
                metric_name="Per capita disposable income growth",
                value=f"{float(current['income_growth']):.1f}% y/y",
                numeric=float(current["income_growth"]),
                date=str(current["date"]),
                period=str(current["period"]),
                source_id="nbs-communique",
                source_title=str(current["title"]),
                source_url=str(current["url"]),
                secondary="National per-capita disposable income, real growth",
            )
            add_history_point(
                snapshot,
                metric_name="Income growth versus nominal GDP",
                value=f"Income +{float(current['income_growth']):.1f}% vs GDP +{nominal_growth:.1f}%",
                numeric=float(current["income_growth"]) - nominal_growth,
                date=str(current["date"]),
                period=str(current["period"]),
                source_id="nbs-releases",
                source_title=str(current["title"]),
                source_url=str(current["url"]),
                secondary="National per-capita disposable income growth minus nominal GDP growth",
            )


def build_annual_official_supplements(snapshot: dict[str, Any]) -> None:
    wage_items = [
        {
            "period": "2024",
            "non_private_url": "https://www.stats.gov.cn/zwfwck/sjfb/202505/t20250516_1959826.html",
            "private_url": None,
        },
        {
            "period": "2023",
            "non_private_url": "https://www.stats.gov.cn/xxgk/sjfb/zxfb2020/202405/t20240520_1950434.html",
            "private_url": None,
        },
        {
            "period": "2022",
            "non_private_url": "https://www.stats.gov.cn/sj/zxfb/202305/t20230509_1939290.html",
            "private_url": "https://www.stats.gov.cn/xxgk/sjfb/zxfb2020/202305/t20230509_1939295.html",
        },
        {
            "period": "2021",
            "non_private_url": "https://www.stats.gov.cn/sj/zxfb/202302/t20230203_1901472.html",
            "private_url": "https://www.stats.gov.cn/xxgk/sjfb/zxfb2020/202205/t20220520_1857636.html",
        },
    ]
    for item in wage_items:
        period = str(item["period"])
        if history_has_period(snapshot, "Average wage growth", period):
            continue
        try:
            response = fetch(str(item["non_private_url"]), verify=False)
            response.encoding = "utf-8"
            soup = soup_from_html(response.text)
            text = article_text(soup)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = page_pub_date(soup, str(item["non_private_url"]))

            private_text = text
            if item["private_url"]:
                private_response = fetch(str(item["private_url"]), verify=False)
                private_response.encoding = "utf-8"
                private_text = article_text(soup_from_html(private_response.text))

            non_private_match = re.search(
                r"全国城镇非私营单位就业人员年平均工资(?:为)?\s*([\d]+)\s*元[^。]*?名义增长(?:\s*\[\d+\])?\s*([\d.]+)%",
                text,
                re.I,
            )
            private_match = re.search(
                r"全国城镇私营单位就业人员年平均工资(?:为)?\s*([\d]+)\s*元[^。]*?名义增长(?:\s*\[\d+\])?\s*([\d.]+)%",
                private_text,
                re.I,
            )
            enterprise_match = re.search(
                r"规模以上企业就业人员年平均工资(?:为)?\s*([\d]+)\s*元[^。]*?名义增长(?:\s*\[\d+\])?\s*([\d.]+)%",
                text,
                re.I,
            )
            if not non_private_match:
                continue

            _, non_private_growth = non_private_match.groups()
            secondary_bits: list[str] = []
            if private_match:
                private_level, private_growth = private_match.groups()
                secondary_bits.append(
                    f"Private +{float(private_growth):.1f}% (RMB {int(private_level):,})"
                )
            if enterprise_match:
                enterprise_level, enterprise_growth = enterprise_match.groups()
                secondary_bits.append(
                    f"Large enterprises +{float(enterprise_growth):.1f}% (RMB {int(enterprise_level):,})"
                )

            add_history_point(
                snapshot,
                metric_name="Average wage growth",
                value=f"{float(non_private_growth):.1f}%",
                numeric=float(non_private_growth),
                date=date,
                period=period,
                source_id="nbs-releases",
                source_title=title,
                source_url=str(item["non_private_url"]),
                secondary="; ".join(secondary_bits),
            )
        except Exception:
            continue

    capacity_items = [
        ("2025", "https://www.stats.gov.cn/sj/zxfb/202601/t20260119_1962320.html"),
        ("2024", "https://www.stats.gov.cn/sj/sjjd/202501/t20250117_1958343.html"),
        ("2023", "https://www.stats.gov.cn/xxgk/jd/sjjd2020/202401/t20240118_1946721.html"),
        ("2022", "https://www.stats.gov.cn/sj/zxfb/202302/t20230203_1901716.html"),
        ("2021", "https://www.stats.gov.cn/xxgk/jd/sjjd2020/202201/t20220118_1826604.html"),
    ]
    for period, url in capacity_items:
        if history_has_period(snapshot, "Capacity utilization", period):
            continue
        try:
            response = fetch(url, verify=False)
            response.encoding = "utf-8"
            soup = soup_from_html(response.text)
            text = article_text(soup)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = page_pub_date(soup, url)
            annual_match = first_match(
                text,
                [
                    rf"{period}\s*年(?:，)?全国(?:规模以上)?工业产能利用率为\s*([\d.]+)%",
                ],
            )
            if not annual_match:
                continue
            quarterly_match = re.search(
                r"一、二、三、四季度产能利用率分别为\s*([\d.]+)%\s*、\s*([\d.]+)%\s*、\s*([\d.]+)%\s*和\s*([\d.]+)%",
                text,
            )
            q4_match = re.search(r"四季度，全国(?:规模以上)?工业产能利用率为\s*([\d.]+)%", text)
            manufacturing_match = re.search(r"制造业产能利用率为\s*([\d.]+)%", text)

            secondary_bits: list[str] = []
            if q4_match:
                secondary_bits.append(f"Q4 {q4_match.group(1)}%")
            elif quarterly_match:
                secondary_bits.append(f"Q4 {quarterly_match.group(4)}%")
            if manufacturing_match:
                secondary_bits.append(f"Manufacturing {manufacturing_match.group(1)}%")

            annual_value = float(annual_match.group(1))
            add_history_point(
                snapshot,
                metric_name="Capacity utilization",
                value=f"{annual_value:.1f}%",
                numeric=annual_value,
                date=date,
                period=period,
                source_id="nbs-releases",
                source_title=title,
                source_url=url,
                secondary="; ".join(secondary_bits) if secondary_bits else "Annual utilization rate",
            )
        except Exception:
            continue

    communique_items = [
        ("2024", "https://www.stats.gov.cn/xxgk/sjfb/tjgb2020/202502/t20250228_1958817.html"),
        ("2023", "https://www.stats.gov.cn/zt_18555/zthd/lhfw/2024/hgjj/202402/t20240229_1947948.html"),
        ("2022", "https://www.stats.gov.cn/xxgk/sjfb/zxfb2020/202302/t20230228_1919001.html"),
        ("2021", "https://www.stats.gov.cn/sj/zxfb/202302/t20230203_1901393.html"),
    ]
    for period, url in communique_items:
        try:
            response = fetch(url, verify=False)
            response.encoding = "utf-8"
            soup = soup_from_html(response.text)
            text = article_text(soup)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = page_pub_date(soup, url)

            if not history_has_period(snapshot, "High-tech industry investment", period):
                high_tech_match = first_match(
                    text,
                    [
                        r"(?:全年)?高技术产业投资(?:\s*\[\d+\])?\s*比上年增长\s*([\d.]+)%",
                    ],
                )
                if high_tech_match:
                    growth = float(high_tech_match.group(1))
                    add_history_point(
                        snapshot,
                        metric_name="High-tech industry investment",
                        value=f"{growth:.1f}% y/y",
                        numeric=growth,
                        date=date,
                        period=period,
                        source_id="nbs-communique",
                        source_title=title,
                        source_url=url,
                        secondary="Annual high-technology industry investment growth",
                    )

            if not history_has_period(snapshot, "Technology-transformation investment", period):
                tech_transform_match = first_match(
                    text,
                    [
                        r"制造业技术改造投资(?:\s*\[\d+\])?\s*增长\s*([\d.]+)%",
                    ],
                )
                if tech_transform_match:
                    growth = float(tech_transform_match.group(1))
                    add_history_point(
                        snapshot,
                        metric_name="Technology-transformation investment",
                        value=f"{growth:.1f}% y/y",
                        numeric=growth,
                        date=date,
                        period=period,
                        source_id="nbs-communique",
                        source_title=title,
                        source_url=url,
                        secondary="Annual manufacturing technology-transformation investment growth",
                    )

            if not history_has_period(snapshot, "Solar-cell output", period):
                solar_match = first_match(
                    text,
                    [
                        r"太阳能电池\(光伏电池\)产量\s*([\d.]+)\s*亿千瓦，增长\s*([\d.]+)%",
                        r"太阳能电池\(光伏电池\)\s*([\d.]+)\s*万千瓦[^。]*?([\d.]+)%",
                    ],
                )
                if solar_match:
                    solar_value = float(solar_match.group(1))
                    solar_growth = float(solar_match.group(2))
                    if "亿千瓦" in solar_match.group(0):
                        solar_value *= 10000
                    add_history_point(
                        snapshot,
                        metric_name="Solar-cell output",
                        value=f"{solar_value:.1f} (10000 kilowatt)",
                        numeric=solar_value,
                        date=date,
                        period=period,
                        source_id="nbs-communique",
                        source_title=title,
                        source_url=url,
                        secondary=f"{solar_growth:.1f}% y/y",
                    )
        except Exception:
            continue


def build_port_history(snapshot: dict[str, Any]) -> None:
    current_metric = snapshot["metrics"].get("Port throughput")
    if current_metric:
        add_history_point(
            snapshot,
            metric_name="Port throughput",
            value=current_metric["value"],
            numeric=parse_float(current_metric["value"]),
            date=current_metric["date"],
            period="2025",
            source_id=current_metric["sourceId"],
            source_title=current_metric["sourceTitle"],
            source_url=current_metric["sourceUrl"],
            secondary=current_metric.get("secondary", ""),
        )

    items = [
        (
            "https://xxgk.mot.gov.cn/jigou/zhghs/202506/t20250610_4170228.html",
            "2024",
        ),
        (
            "https://xxgk.mot.gov.cn/2020/jigou/zhghs/202406/t20240614_4142419.html",
            "2023",
        ),
        (
            "https://xxgk.mot.gov.cn/2020/jigou/zhghs/202306/t20230615_3847023.html",
            "2022",
        ),
        (
            "https://xxgk.mot.gov.cn/2020/jigou/zhghs/202205/t20220524_3655470.html",
            "2021",
        ),
    ]
    for url, period in items:
        try:
            response = requests.get(url, timeout=(20, 90), headers=SESSION.headers, verify=False)
            response.encoding = "utf-8"
            soup = soup_from_html(response.text)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = page_pub_date(soup, url)
            text = article_text(soup)
            throughput_match = re.search(
                r"全年完成港口货物吞吐量([\d.]+)亿吨，比上年(增长|下降)([\d.]+)%",
                text,
            )
            tonnage_direction = ""
            if throughput_match:
                tonnage, tonnage_direction, tonnage_change = throughput_match.groups()
            else:
                throughput_growth_match = re.search(
                    r"完成港口货物吞吐量([\d.]+)亿吨，同比增长([\d.]+)%",
                    text,
                )
                if not throughput_growth_match:
                    continue
                tonnage, tonnage_change = throughput_growth_match.groups()
                tonnage_direction = "增长"
            container_match = re.search(
                r"完成集装箱吞吐量([\d.]+)亿标准箱，(增长|下降)([\d.]+)%",
                text,
            )
            if not throughput_match:
                container_growth_match = re.search(
                    r"完成集装箱吞吐量([\d.]+)亿标准箱，同比增长([\d.]+)%",
                    text,
                )
            else:
                container_growth_match = None
            secondary = signed_percent(tonnage_direction, tonnage_change) + " y/y"
            if container_match:
                containers, container_direction, container_change = container_match.groups()
                secondary = (
                    f"Containers {float(containers) * 100:.0f} mn TEU; "
                    f"{signed_percent(container_direction, container_change)} y/y"
                )
            elif container_growth_match:
                containers, container_change = container_growth_match.groups()
                secondary = f"Containers {float(containers) * 100:.0f} mn TEU; +{float(container_change):.1f}% y/y"
            add_history_point(
                snapshot,
                metric_name="Port throughput",
                value=f"{float(tonnage) / 10:.1f} bn tons",
                numeric=float(tonnage) / 10,
                date=date,
                period=period,
                source_id="mot-annual-bulletin",
                source_title=title,
                source_url=url,
                secondary=secondary,
            )
        except Exception:
            continue

    if not history_has_period(snapshot, "Port throughput", "2021"):
        try:
            url = "https://www.ndrc.gov.cn/fggz/jjmy/ltyfz/202201/t20220129_1313780.html"
            response = fetch(url, verify=False)
            response.encoding = "utf-8"
            soup = soup_from_html(response.text)
            title = clean_text(soup.title.get_text(" ", strip=True))
            date = page_pub_date(soup, url)
            text = article_text(soup)
            throughput_match = first_match(
                text,
                [
                    r"港口货物吞吐量.*?([\d.]+)\s*亿吨，比\s*2020\s*年同期增长\s*([\d.]+)%",
                    r"完成港口货物吞吐量\s*([\d.]+)\s*亿吨，同比增长\s*([\d.]+)%",
                ],
            )
            if throughput_match:
                tonnage, tonnage_change = throughput_match.groups()
                add_history_point(
                    snapshot,
                    metric_name="Port throughput",
                    value=f"{float(tonnage) / 10:.1f} bn tons",
                    numeric=float(tonnage) / 10,
                    date=date,
                    period="2021",
                    source_id="ndrc-transport-bulletin",
                    source_title=title,
                    source_url=url,
                    secondary=f"+{float(tonnage_change):.1f}% y/y",
                )
        except Exception:
            pass


def build_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metrics": {},
        "history": {},
        "sourceSnapshots": [],
        "notes": [
            "Values are shown from the latest accessible free release pulled during this refresh, with exact source dates preserved on each metric.",
            "When an official English source lags or is structurally unavailable, the page falls back to the closest accessible official or free market-data page and labels the source directly.",
        ],
    }

    extract_nbs_70_city(snapshot)
    extract_nbs_property(snapshot)
    extract_nbs_activity(snapshot)
    extract_nbs_fai(snapshot)
    extract_nbs_industrial_production(snapshot)
    extract_nbs_retail(snapshot)
    extract_nbs_cpi(snapshot)
    extract_nbs_pmi(snapshot)
    extract_nbs_profits(snapshot)
    extract_nbs_energy(snapshot)
    extract_nbs_means_of_production(snapshot)
    extract_nbs_annual(snapshot)
    extract_nbs_chinese_releases(snapshot)
    extract_pboc_financial(snapshot)
    extract_pboc_policy(snapshot)
    extract_policy_context(snapshot)
    extract_safe(snapshot)
    extract_safe_holdings(snapshot)
    extract_hkex(snapshot)
    extract_market_data(snapshot)
    extract_debt_ratios(snapshot)
    extract_mof_fiscal(snapshot)
    extract_ceic_trade_metrics(snapshot)
    extract_sse_scfi(snapshot)
    extract_caict(snapshot)
    extract_alternative_metrics(snapshot)
    extract_aux_source_status(snapshot)
    probe_customs(snapshot)
    build_pmi_history(snapshot)
    build_nbs_archive_history(snapshot)
    build_structural_history(snapshot)
    build_annual_official_supplements(snapshot)
    build_port_history(snapshot)
    sort_history(snapshot)
    backfill_metrics_from_history(snapshot)
    build_composite_metrics(snapshot)
    if (
        "High-tech industry investment" not in snapshot["metrics"]
        and "High-tech manufacturing investment" in snapshot["metrics"]
    ):
        snapshot["metrics"]["High-tech industry investment"] = snapshot["metrics"][
            "High-tech manufacturing investment"
        ]

    snapshot["liveMetricCount"] = len(snapshot["metrics"])
    snapshot["sourceSnapshotCount"] = len(snapshot["sourceSnapshots"])
    snapshot["historyMetricCount"] = sum(
        1 for points in snapshot.get("history", {}).values() if len(points) > 1
    )
    return snapshot


def main() -> None:
    snapshot = build_snapshot()
    OUTPUT_PATH.write_text(
        "window.LIVE_SNAPSHOT = " + json.dumps(snapshot, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Live metrics: {snapshot['liveMetricCount']}")
    print(f"Source snapshots: {snapshot['sourceSnapshotCount']}")


if __name__ == "__main__":
    main()
