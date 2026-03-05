import argparse
import json
import os
import re
from typing import Dict, List, Tuple

from lxml import html


def _collect_table_html(extract_dir: str) -> List[Tuple[str, str]]:
    sources: List[Tuple[str, str]] = []

    full_md = os.path.join(extract_dir, "full.md")
    if os.path.exists(full_md):
        with open(full_md, "r", encoding="utf-8") as f:
            content = f.read()
        if "<table" in content:
            sources.append(("full.md", content))

    for name in os.listdir(extract_dir):
        if not name.endswith(".json"):
            continue
        path = os.path.join(extract_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        def walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in {"html", "table_body", "content"} and isinstance(v, str) and "<table" in v:
                        sources.append((name, v))
                    else:
                        walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(data)

    return sources


def _expand_table(table_html: str) -> List[List[str]]:
    doc = html.fromstring(table_html)
    table = doc.xpath("//table")
    if not table:
        return []
    table = table[0]

    grid: List[List[str]] = []
    for tr in table.xpath(".//tr"):
        row: List[str] = []
        for td in tr.xpath("./th|./td"):
            text = "".join(td.itertext()).strip()
            colspan = int(td.get("colspan", "1"))
            rowspan = int(td.get("rowspan", "1"))
            if rowspan > 1:
                # Simplified: ignore rowspan expansion for now
                pass
            row.append(text)
            for _ in range(colspan - 1):
                row.append("")
        if row:
            grid.append(row)

    max_len = max((len(r) for r in grid), default=0)
    for r in grid:
        if len(r) < max_len:
            r.extend([""] * (max_len - len(r)))
    return grid


def _parse_kv_rows(rows: List[List[str]]) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    label_pattern = re.compile(r".+:\s*$")
    for row in rows:
        i = 0
        while i < len(row):
            cell = row[i].strip()
            if cell and label_pattern.match(cell):
                j = i + 1
                while j < len(row) and not row[j].strip():
                    j += 1
                if j < len(row):
                    kv[cell.rstrip(":").strip()] = row[j].strip()
                    i = j + 1
                    continue
            i += 1
    return kv


def _find_header_index(rows: List[List[str]]) -> int:
    for idx, row in enumerate(rows):
        normalized = [re.sub(r"\W+", "", cell).lower() for cell in row]
        if "id" in normalized and any(v in {"partnumber", "partdescription"} for v in normalized):
            return idx
    return -1


def _normalize_header(header_row: List[str], data_rows: List[List[str]]) -> Tuple[List[str], List[List[str]]]:
    keep_indices = [i for i, h in enumerate(header_row) if h.strip()]
    headers = [header_row[i].strip() for i in keep_indices]
    headers = [re.sub(r"\s+", " ", h) for h in headers]
    headers = ["Part Description" if h.replace(" ", "") == "PartDescription" else h for h in headers]
    normalized = [[row[i].strip() for i in keep_indices] for row in data_rows]
    return headers, normalized


def _parse_items(rows: List[List[str]]) -> List[Dict[str, str]]:
    header_idx = _find_header_index(rows)
    if header_idx == -1:
        return []

    header_row = rows[header_idx]
    data_rows = rows[header_idx + 1 :]
    headers, normalized_rows = _normalize_header(header_row, data_rows)

    items: List[Dict[str, str]] = []
    last_item = None
    for row in normalized_rows:
        if not any(cell.strip() for cell in row):
            continue
        if row[0].strip().lower() == "comment":
            if last_item is not None:
                # Comment value is in the last non-empty cell
                comment_value = ""
                for cell in reversed(row):
                    if cell.strip():
                        comment_value = cell.strip()
                        break
                last_item["Comment"] = comment_value
            continue

        first_cell = row[0].strip()
        if any(
            key in first_cell
            for key in (
                "非应纳税",
                "应纳税",
                "定税日期",
                "项目合计",
                "税款合计",
                "合计",
            )
        ):
            break
        if first_cell.startswith("1.") or first_cell.startswith("8.") or first_cell.startswith("9."):
            break

        item = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
        if item.get("ID"):
            items.append(item)
            last_item = item

    return items


def _parse_totals(rows: List[List[str]]) -> Dict[str, str]:
    totals: Dict[str, str] = {}
    keywords = (
        "Non-Taxable",
        "Taxable",
        "TaxDate",
        "LineTotal",
        "TotalTax",
        "Total",
        "Currency",
        "税款合计",
        "项目合计",
        "合计",
        "定税日期",
        "应纳税",
        "非应纳税",
        "货币",
    )
    for row in rows:
        for i in range(0, len(row)):
            label = row[i].strip()
            if not label or ":" not in label:
                continue
            if not any(k in label for k in keywords):
                continue
            if not label.endswith(":"):
                parts = label.split(":", 1)
                if len(parts) == 2 and parts[1].strip():
                    totals[parts[0].strip()] = parts[1].strip()
                    continue
            j = i + 1
            while j < len(row):
                candidate = row[j].strip()
                if not candidate:
                    j += 1
                    continue
                if candidate.endswith(":"):
                    j += 1
                    continue
                totals[label.rstrip(":").strip()] = candidate
                break
    return totals


def parse_extract_dir(extract_dir: str) -> Dict:
    sources = _collect_table_html(extract_dir)
    all_results = []

    for source_name, table_html in sources:
        rows = _expand_table(table_html)
        if not rows:
            continue

        header_idx = _find_header_index(rows)
        header_rows = rows[:header_idx] if header_idx != -1 else rows
        kv = _parse_kv_rows(header_rows)

        remark = kv.pop("Remark", None)
        items = _parse_items(rows)
        totals = _parse_totals(rows[header_idx + 1 :] if header_idx != -1 else [])

        all_results.append(
            {
                "source": source_name,
                "kv": kv,
                "remark": remark,
                "items": items,
                "totals": totals,
            }
        )

    return {
        "extract_dir": extract_dir,
        "results": all_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse MinerU extract outputs to key-value pairs.")
    parser.add_argument("extract_dir", help="Path to extract_* folder")
    parser.add_argument("-o", "--output", help="Output JSON path", default="parsed_kv.json")
    args = parser.parse_args()

    data = parse_extract_dir(args.extract_dir)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
