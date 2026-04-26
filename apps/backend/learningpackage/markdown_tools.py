from __future__ import annotations

import re
from typing import Any


LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
STAGE_HEADING_PATTERN = re.compile(
    r"^(?:##|###)\s*(?:\u9636\u6bb5|\u5c0f\u76ee\u6807|Step)\s*(\d+)\s*(?:[\uff5c|:\uff1a\-\u2014]\s*|\s+)(.+)$"
)
TABLE_SEPARATOR_PATTERN = re.compile(r"^:?-{3,}:?$")


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _is_bullet_line(line: str) -> bool:
    return line.startswith("- ") or line.startswith("* ")


def _is_ordered_line(line: str) -> bool:
    return bool(re.match(r"^\d+[.)]\s+", line))


def _strip_list_marker(line: str) -> str:
    stripped = line.strip()
    if _is_bullet_line(stripped):
        return stripped[2:].strip()
    return re.sub(r"^\d+[.)]\s+", "", stripped).strip()


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _split_collapsed_table_line(line: str) -> list[str]:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return [line]

    non_empty_cells = [cell.strip() for cell in stripped.split("|") if cell.strip()]
    if len(non_empty_cells) < 6:
        return [line]

    separator_index = next(
        (index for index, cell in enumerate(non_empty_cells) if TABLE_SEPARATOR_PATTERN.match(cell)),
        -1,
    )
    if separator_index <= 0:
        return [line]

    column_count = separator_index
    if column_count <= 0 or len(non_empty_cells) % column_count != 0:
        return [line]

    row_count = len(non_empty_cells) // column_count
    if row_count < 2:
        return [line]

    rows = []
    for offset in range(0, len(non_empty_cells), column_count):
        rows.append(non_empty_cells[offset : offset + column_count])

    return [f"| {' | '.join(row)} |" for row in rows]


def _expand_table_lines(lines: list[str]) -> list[str]:
    expanded: list[str] = []
    for line in lines:
        expanded.extend(_split_collapsed_table_line(line))
    return expanded


def _consume_math_block(lines: list[str], start_index: int) -> tuple[dict[str, Any] | None, int]:
    stripped = lines[start_index].strip()
    if not stripped.startswith("$$"):
        return None, start_index

    inline_formula = re.match(r"^\$\$(.+?)\$\$$", stripped)
    if inline_formula:
        return {"type": "math", "text": inline_formula.group(1).strip(), "display": True}, start_index + 1

    collected: list[str] = []
    first_line = stripped[2:].strip()
    if first_line:
        if first_line.endswith("$$"):
            return {"type": "math", "text": first_line[:-2].strip(), "display": True}, start_index + 1
        collected.append(first_line)

    index = start_index + 1
    while index < len(lines):
        candidate = lines[index].rstrip()
        if candidate.strip().endswith("$$"):
            closing = candidate.strip()[:-2].strip()
            if closing:
                collected.append(closing)
            return {"type": "math", "text": "\n".join(collected).strip(), "display": True}, index + 1
        collected.append(candidate)
        index += 1

    return None, start_index


def _normalize_paragraph_buffer(buffer: list[str]) -> str:
    return " ".join(part.strip() for part in buffer if part.strip()).strip()


def normalize_paragraphs(lines: list[str]) -> list[str]:
    return _parse_content(lines)["paragraphs"]


def _parse_markdown_table(lines: list[str]) -> dict[str, Any] | None:
    rows: list[list[str]] = []
    for raw_line in lines:
        stripped = raw_line.strip().strip("|")
        cells = [cell.strip() for cell in stripped.split("|")]
        if cells:
            rows.append(cells)

    if len(rows) < 2:
        return None

    headers = rows[0]
    separator = rows[1]
    if len(separator) != len(headers) or not all(TABLE_SEPARATOR_PATTERN.match(cell) for cell in separator):
        return None

    normalized_rows: list[list[str]] = []
    for row in rows[2:]:
        if len(row) < len(headers):
            row = row + [""] * (len(headers) - len(row))
        elif len(row) > len(headers):
            row = row[: len(headers)]
        normalized_rows.append(row)

    return {
        "headers": headers,
        "rows": normalized_rows,
    }


def _flush_paragraph_block(buffer: list[str], paragraphs: list[str], blocks: list[dict[str, Any]]) -> None:
    paragraph = _normalize_paragraph_buffer(buffer)
    buffer.clear()
    if not paragraph:
        return
    paragraphs.append(paragraph)
    blocks.append({"type": "paragraph", "text": paragraph})


def _parse_content(lines: list[str]) -> dict[str, Any]:
    normalized_lines = _expand_table_lines(lines)
    paragraphs: list[str] = []
    bullets: list[str] = []
    tables: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    paragraph_buffer: list[str] = []

    index = 0
    while index < len(normalized_lines):
        stripped = normalized_lines[index].strip()

        if not stripped:
            _flush_paragraph_block(paragraph_buffer, paragraphs, blocks)
            index += 1
            continue

        math_block, next_index = _consume_math_block(normalized_lines, index)
        if math_block is not None:
            _flush_paragraph_block(paragraph_buffer, paragraphs, blocks)
            if math_block.get("text"):
                blocks.append(math_block)
            index = next_index
            continue

        if _is_table_row(stripped):
            _flush_paragraph_block(paragraph_buffer, paragraphs, blocks)
            table_lines: list[str] = []
            while index < len(normalized_lines) and _is_table_row(normalized_lines[index].strip()):
                table_lines.append(normalized_lines[index].strip())
                index += 1

            table = _parse_markdown_table(table_lines)
            if table:
                tables.append(table)
                blocks.append({"type": "table", **table})
            else:
                paragraph_buffer.extend(table_lines)
            continue

        if _is_bullet_line(stripped) or _is_ordered_line(stripped):
            _flush_paragraph_block(paragraph_buffer, paragraphs, blocks)
            ordered = _is_ordered_line(stripped)
            items: list[str] = []
            while index < len(normalized_lines):
                candidate = normalized_lines[index].strip()
                if ordered and _is_ordered_line(candidate):
                    items.append(_strip_list_marker(candidate))
                    index += 1
                    continue
                if not ordered and _is_bullet_line(candidate):
                    items.append(_strip_list_marker(candidate))
                    index += 1
                    continue
                break

            items = _dedupe_preserve(items)
            if items:
                bullets.extend(items)
                blocks.append({"type": "list", "ordered": ordered, "items": items})
            continue

        paragraph_buffer.append(stripped)
        index += 1

    _flush_paragraph_block(paragraph_buffer, paragraphs, blocks)

    return {
        "paragraphs": paragraphs,
        "bullets": bullets,
        "tables": tables,
        "blocks": blocks,
    }


def parse_subsections(lines: list[str]) -> list[dict[str, Any]]:
    subsections: list[dict[str, Any]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    def flush_current() -> None:
        nonlocal current_title, current_lines
        if not current_title:
            return
        parsed = _parse_content(current_lines)
        subsections.append(
            {
                "title": current_title,
                **parsed,
            }
        )
        current_title = None
        current_lines = []

    for raw_line in lines:
        heading = re.match(r"^###\s+(.+)$", raw_line.strip())
        if heading:
            flush_current()
            current_title = heading.group(1).strip()
            continue
        if current_title is not None:
            current_lines.append(raw_line)

    flush_current()
    return subsections


def parse_markdown_document(raw: str) -> dict[str, Any]:
    lines = raw.replace("\r\n", "\n").split("\n")
    title_line = next((line for line in lines if line.startswith("# ")), "# Untitled")
    title = title_line.replace("# ", "", 1).strip()

    sections: list[dict[str, Any]] = []
    intro_lines: list[str] = []
    current_section: dict[str, Any] | None = None

    for raw_line in lines:
        if raw_line.startswith("# "):
            continue

        heading = re.match(r"^##\s+(.+)$", raw_line.strip())
        if heading:
            current_section = {"title": heading.group(1).strip(), "lines": []}
            sections.append(current_section)
            continue

        if current_section is None:
            intro_lines.append(raw_line)
        else:
            current_section["lines"].append(raw_line)

    intro_payload = _parse_content(intro_lines)

    parsed_sections: list[dict[str, Any]] = []
    for section in sections:
        top_level_lines: list[str] = []
        subsection_lines: list[str] = []
        has_subsection = False

        for raw_line in section["lines"]:
            if re.match(r"^###\s+(.+)$", raw_line.strip()):
                has_subsection = True
            if has_subsection:
                subsection_lines.append(raw_line)
            else:
                top_level_lines.append(raw_line)

        top_level_payload = _parse_content(top_level_lines)
        parsed_sections.append(
            {
                "title": section["title"],
                **top_level_payload,
                "subsections": parse_subsections(subsection_lines),
            }
        )

    return {
        "title": title,
        "intro": intro_payload["paragraphs"],
        "introBlocks": intro_payload["blocks"],
        "sections": parsed_sections,
    }


def extract_markdown_links(raw: str) -> list[dict[str, str]]:
    seen: set[str] = set()
    sources: list[dict[str, str]] = []

    for title, url in LINK_PATTERN.findall(raw):
        normalized_url = url.strip()
        if normalized_url in seen:
            continue
        seen.add(normalized_url)
        sources.append(
            {
                "title": title.strip(),
                "url": normalized_url,
            }
        )

    return sources


def _parse_keyed_bullets(block_lines: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "summary": "",
        "outcome": "",
        "estimatedTime": "",
        "prerequisites": [],
        "tasks": [],
        "deliverables": [],
    }
    current_key: str | None = None

    key_map = {
        "\u6458\u8981": "summary",
        "\u9636\u6bb5\u6458\u8981": "summary",
        "\u5b8c\u6210\u6807\u5fd7": "outcome",
        "\u5b8c\u6210\u6807\u51c6": "outcome",
        "\u9884\u8ba1\u65f6\u957f": "estimatedTime",
        "\u65f6\u957f": "estimatedTime",
        "\u524d\u7f6e\u77e5\u8bc6": "prerequisites",
        "\u524d\u63d0\u6761\u4ef6": "prerequisites",
        "\u5b66\u4e60\u52a8\u4f5c": "tasks",
        "\u4efb\u52a1": "tasks",
        "\u7ec3\u4e60\u52a8\u4f5c": "tasks",
        "\u9636\u6bb5\u4ea7\u51fa": "deliverables",
        "\u4ea7\u51fa": "deliverables",
        "\u4ea4\u4ed8\u7269": "deliverables",
    }

    for raw_line in block_lines:
        line = raw_line.strip()
        if not _is_bullet_line(line):
            continue

        content = _strip_list_marker(line)
        key_match = re.match(r"^([^\uff1a:]+)[\uff1a:]\s*(.*)$", content)

        if key_match:
            key = key_match.group(1).strip()
            if key in key_map:
                current_key = key_map[key]
                value = key_match.group(2).strip()
                if current_key in {"summary", "outcome", "estimatedTime"}:
                    result[current_key] = value
                elif value and value not in {"\u65e0", "\u6682\u65e0"}:
                    result[current_key].append(value)
                continue

        if current_key in {"prerequisites", "tasks", "deliverables"} and content and content not in {"\u65e0", "\u6682\u65e0"}:
            result[current_key].append(content)

    return result


def extract_goals_from_plan(raw: str) -> list[dict[str, Any]]:
    lines = raw.replace("\r\n", "\n").split("\n")
    goals: list[dict[str, Any]] = []
    current_title: str | None = None
    current_stage_number: int | None = None
    current_lines: list[str] = []

    def flush_goal() -> None:
        nonlocal current_title, current_stage_number, current_lines
        if not current_title:
            return

        details = _parse_keyed_bullets(current_lines)
        stage_number = current_stage_number or len(goals) + 1
        goals.append(
            {
                "id": f"goal-{stage_number:03d}",
                "stageNumber": stage_number,
                "stageLabel": f"\u9636\u6bb5 {stage_number}",
                "title": current_title,
                "summary": details["summary"],
                "outcome": details["outcome"],
                "estimatedTime": details["estimatedTime"],
                "prerequisites": details["prerequisites"],
                "tasks": details["tasks"],
                "deliverables": details["deliverables"],
                "lessonStatus": "idle",
                "imageStatus": "idle",
            }
        )
        current_title = None
        current_stage_number = None
        current_lines = []

    for raw_line in lines:
        heading = STAGE_HEADING_PATTERN.match(raw_line.strip())
        if heading:
            flush_goal()
            current_stage_number = int(heading.group(1))
            current_title = heading.group(2).strip()
            continue

        if current_title:
            current_lines.append(raw_line)

    flush_goal()
    return goals
