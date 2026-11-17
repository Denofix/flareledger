"""Bounded lexical evidence selection. No network, model calls or database writes."""

import hashlib
import io
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from functools import lru_cache
from pathlib import Path

from app.storage import Repository

STOP = set(
    "a an and are as at be can compare could data describe do does explain evidence experiment experiments find for from how i in is it know me of on or research show tell than that the their these this to two use using what which with would about available between same has have included does saying supply saying does establish into saying its saying listed".split()
)
MAX_ITEMS = 5
MAX_SUPPORT_BYTES = 5000
MAX_CONTEXT_BYTES = 16000


def words(text: str) -> set[str]:
    # Split camel-case file/quantity names as well as punctuation, preserving digits.
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    result = set(re.findall(r"[a-z0-9]+", text.casefold()))
    return result | {
        word[:-1] for word in result if len(word) > 3 and word.endswith("s") and not word.endswith("ss")
    }


def query_words(question: str) -> set[str]:
    result = [
        word for word in re.findall(r"[\w-]+", question) if len(word) >= 3 and word.casefold() not in STOP
    ]
    result += re.findall(r"\b(?:CO|O2|CO2|OR)\b", question)
    return (words(" ".join(result[:32])) - STOP) | ({"or"} if re.search(r"\bOR\b", question) else set())


def named(question: str, name: str) -> bool:
    parts = re.findall(r"[a-z0-9]+", name.casefold())
    return bool(
        parts
        and re.search(
            r"(?<![\w-])" + r"[\s_-]*".join(map(re.escape, parts)) + r"(?![\w-])", question.casefold()
        )
    )


@lru_cache(maxsize=2)
def embedded_texts(seed_path: str, expected_sha: str) -> dict[str, dict]:
    # Cache only the small file-text collection, not the complete parsed seed.
    try:
        raw = Path(seed_path).read_bytes()
    except OSError:
        return {}
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        return {}
    return {entry["source_id"]: entry for entry in json.loads(raw)["embedded_text_files"]}


@lru_cache(maxsize=4)
def docx_paragraphs(path: str, expected_sha: str, expected_bytes: int) -> tuple[str, ...]:
    file = Path(path)
    try:
        if not file.is_file() or not 0 < file.stat().st_size == expected_bytes <= 262144:
            return ()
        raw = file.read_bytes()
    except OSError:
        return ()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        return ()
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info = archive.getinfo("word/document.xml")
            if info.file_size > 524288:
                return ()
            root = ET.fromstring(archive.read(info))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        prefix = "{" + ns["w"] + "}"
        return tuple(
            "".join(
                (node.text or "")
                if node.tag == prefix + "t"
                else "\t"
                if node.tag == prefix + "tab"
                else "\n"
                if node.tag in {prefix + "br", prefix + "cr"}
                else ""
                for node in paragraph.iter()
            )
            for paragraph in root.findall(".//w:p", ns)
        )
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        return ()


def select_paragraphs(paragraphs: tuple[str, ...], terms: set[str]) -> list[dict]:
    # Prefer relevant early explanatory paragraphs over later bibliography matches.
    ranked = sorted(
        range(len(paragraphs)), key=lambda i: (-(len(words(paragraphs[i]) & terms) / (1 + i / 10)), i)
    )
    selected: list[int] = []
    used = 0
    for i in ranked:
        text = paragraphs[i]
        if not text.strip() or not (words(text) & terms):
            continue
        size = len(text.encode())
        if used + size <= 2600 and len(selected) < 10:
            selected.append(i)
            used += size
    return [{"paragraph_number": i + 1, "text": paragraphs[i]} for i in sorted(selected)]


def retrieve(repository: Repository, db: sqlite3.Connection, question: str) -> tuple[list[dict], list[dict]]:
    terms = query_words(question)
    if not terms:
        return [], []
    rows = db.execute(
        "SELECT kind, payload_json, ordinal FROM fl_entities WHERE kind IN ('investigation','record','series','source','knowledge_card','quality_issue') ORDER BY kind, ordinal"
    )
    entities = [(kind, json.loads(raw), ordinal) for kind, raw, ordinal in rows]
    sources = {item["id"]: item for kind, item, _ in entities if kind == "source"}
    investigations = [item for kind, item, _ in entities if kind == "investigation"]
    cards = [item for kind, item, _ in entities if kind == "knowledge_card"]
    series = [item for kind, item, _ in entities if kind == "series"]
    scopes = {
        item["id"]
        for item in investigations
        if named(question, item["id"])
        or (
            item.get("acronym")
            and (item["acronym"].casefold() not in STOP or item["acronym"] in question)
            and named(question, item["acronym"])
        )
    }
    labels = {
        item["original_trial_label"] for item in series if named(question, item["original_trial_label"])
    }
    label_scopes = {item["investigation_id"] for item in series if item["original_trial_label"] in labels}
    scopes.update(label_scopes)
    if not scopes:
        scopes.update(
            item["investigation_id"]
            for kind, item, _ in entities
            if kind == "record" and words(item.get("material") or "") & terms
        )
    card_words = Counter(word for card in cards for word in words(card["title"]) - STOP)
    issues = [item for kind, item, _ in entities if kind == "quality_issue"]
    candidates: dict[tuple[str, str], dict] = {}

    def add(
        kind: str,
        identifier: str,
        content: dict,
        source_ids: list[str],
        priority: float,
        title: str,
        investigation_id: str | None = None,
        evidence_ids: list[str] | None = None,
    ) -> None:
        source_ids = list(dict.fromkeys(s for s in source_ids if s in sources))
        if not source_ids:
            return
        support = json.dumps(content, ensure_ascii=False, sort_keys=True)
        if len(support.encode()) > MAX_SUPPORT_BYTES:
            return
        entry = {
            "id": identifier,
            "kind": kind,
            "source_ids": source_ids,
            "support_text": support,
            "evidence": [repository.item(db, "evidence", i) for i in (evidence_ids or [])],
            "source_titles": [
                {"id": s, "title": sources[s].get("title", ""), "doi": sources[s].get("doi")}
                for s in source_ids
            ],
        }
        hit = {
            "kind": kind,
            "id": identifier,
            "investigation_id": investigation_id,
            "title": title,
            "excerpt": (
                content.get("text_en")
                or content.get("summary_en")
                or content.get("material")
                or content.get("basis")
                or ""
            )[:500],
            "source_ids": source_ids,
            "evidence_ids": evidence_ids or [],
            "sources": [sources[s] for s in source_ids],
        }
        key = (kind, identifier)
        candidate = {"priority": priority, "entry": entry, "hit": hit}
        if key not in candidates or priority > candidates[key]["priority"]:
            candidates[key] = candidate

    for kind, item, ordinal in entities:
        if kind in {"quality_issue", "source"}:
            continue
        title = (
            item.get("title_en")
            or item.get("title")
            or item.get("original_trial_label")
            or item.get("material")
            or item["id"]
        )
        title_hits = words(title) & terms
        body_hits = (
            words(
                json.dumps(
                    {
                        key: item.get(key)
                        for key in ("summary_en", "text_en", "material", "quality_note_en", "tags")
                    }
                )
            )
            & terms
        )
        inv = item.get("investigation_id") or (item["id"] if kind == "investigation" else None)
        if scopes and kind != "knowledge_card" and inv not in scopes:
            continue
        if not title_hits and not body_hits and inv not in scopes:
            continue
        priority = 10 * len(title_hits) + len(body_hits) - ordinal / 100000
        if kind == "knowledge_card" and any(
            card_words[word] == 1 and len(word) >= 3 for word in title_hits - STOP
        ):
            priority += 1000
        alias = re.sub(r"^CARD-SRC-", "", item["id"]).replace("-", " ")
        if kind == "knowledge_card" and named(question, alias):
            priority += 1000
        if kind == "series" and item.get("original_trial_label") in labels:
            priority += 950
        elif kind == "investigation" and inv in scopes:
            priority += 650
        elif kind == "record" and inv in scopes:
            priority += 100
        content = {
            key: value
            for key, value in item.items()
            if key
            not in {
                "points",
                "source_rows",
                "file_catalog_retrieval",
                "file_catalog",
                "original_bytes_base64",
            }
        }
        content["basis"] = (
            "FlareLedger source-based summary or normalized metadata; not a verbatim original-file quotation"
        )
        applicable = [
            issue
            for issue in issues
            if issue["id"] in item.get("quality_issue_ids", [])
            or (inv and inv in issue.get("investigation_ids", []))
        ]
        # Keep broad issue collections out of each measured series; its own note remains.
        if kind == "investigation":
            content["project_annotations"] = applicable
        source_ids = item.get("source_ids", []) or ([item["source_id"]] if item.get("source_id") else [])
        add(kind, item["id"], content, source_ids, priority, title, inv, item.get("evidence_ids", []))

    # Original table packets keep headers, row numbers, raw cells and record types
    # together. Small tables are complete; large ones are explicitly subsets.
    for (raw,) in db.execute("SELECT payload_json FROM fl_entities WHERE kind='raw_table' ORDER BY ordinal"):
        table = json.loads(raw)
        inv = table["investigation_id"]
        records = [
            item for kind, item, _ in entities if kind == "record" and item.get("investigation_id") == inv
        ]
        material_hits = max((len(words(item.get("material") or "") & terms) for item in records), default=0)
        if scopes and inv not in scopes:
            continue
        if inv not in scopes and not material_hits:
            continue
        original = table["rows_as_reported"]
        matches = []
        for index, cells in enumerate(original):
            signals = words(" ".join(cells))
            if index < len(records):
                signals |= words(" ".join(records[index].get("quality_flags", [])))
            if any(re.match(r"-\d", cell.strip()) for cell in cells):
                signals.add("negative")
            if "" in cells:
                signals.update({"blank", "missing"})
            matches.append(signals & terms)
        row_types = {i + 1: records[i].get("record_type") for i in range(min(len(records), len(original)))}
        if len(original) <= 12:
            selected = list(range(len(original)))
        else:
            selected = []
            covered: set[str] = set()
            for _ in range(min(3, len(original))):
                index = max(
                    (i for i in range(len(original)) if i not in selected),
                    key=lambda i: (len(matches[i] - covered), len(matches[i]), -i),
                )
                selected.append(index)
                covered |= matches[index]
            # Include complete referenced definitions when a matching record has them.
            for index in tuple(selected):
                if index < len(records):
                    selected += [
                        number - 1
                        for number in records[index].get("referenced_data_row_numbers", [])
                        if 1 <= number <= len(original)
                    ]
            selected = sorted(set(selected))
        content = {
            "basis": "Original experimental-table cells; selected rows are not an independent-trial count",
            "source_id": table["source_id"],
            "original_sha256": sources[table["source_id"]].get("sha256"),
            "file_version": sources[table["source_id"]].get("file_version"),
            "table_id": table["id"],
            "columns_as_reported": table["columns_as_reported"],
            "total_data_rows": table["data_row_count"],
            "all_rows_included": len(selected) == len(original),
            "rows": [
                {
                    "data_row_number": i + 1,
                    "cells_as_reported": original[i],
                    "normalized_record_type": row_types.get(i + 1),
                }
                for i in selected
            ],
        }
        priority = (800 if inv in scopes else 300) + material_hits
        add("source", table["source_id"], content, [table["source_id"]], priority, table["filename"], inv)

    # Resolve only existing, hash-verified local files. No download occurs here.
    texts: dict[str, dict] | None = None
    metadata = repository.metadata(db)
    for source in sources.values():
        inv = source.get("investigation_id")
        label_match = any(named(source["title"].replace("_", " "), label) for label in labels)
        if inv not in scopes or (inv in label_scopes and not label_match):
            continue
        content = {
            "basis": "Original source-file text, selected without numeric transformations",
            "source_id": source["id"],
            "original_sha256": source.get("sha256"),
            "file_version": source.get("file_version"),
        }
        title = source.get("title", "")
        if title.lower().endswith(".docx") and re.fullmatch(r"[0-9a-f]{64}", source.get("sha256", "")):
            path = repository.settings.data_dir / "ask-context" / (source["sha256"] + ".docx")
            paragraphs = docx_paragraphs(str(path), source["sha256"], source.get("byte_length", 0))
            selection = select_paragraphs(paragraphs, terms)
            if not selection:
                continue
            content.update(
                paragraphs=selection,
                total_paragraphs=len(paragraphs),
                all_paragraphs_included=len(selection) == len(paragraphs),
            )
        elif title.lower().endswith(".txt"):
            if not label_match:
                continue
            if texts is None:
                texts = embedded_texts(str(repository.settings.seed_path), metadata["seed_sha256"])
            file = texts.get(source["id"])
            if not file:
                continue
            text = file["content"]
            encoded = text.encode(file["encoding"])
            if hashlib.sha256(encoded).hexdigest() != source.get("sha256") or len(encoded) != source.get(
                "byte_length"
            ):
                continue
            if len(encoded) <= 2600:
                content["text"] = text
            else:
                content.update(header_as_reported=text.splitlines()[0], data_rows_not_sent=True)
        else:
            continue
        priority = 850 + (40 if words(title) & terms else 0)
        add("source", source["id"], content, [source["id"]], priority, title, inv)

    hits: list[dict] = []
    context: list[dict] = []
    used = 0
    for candidate in sorted(candidates.values(), key=lambda c: -c["priority"]):
        entry = candidate["entry"]
        size = len(json.dumps(entry).encode())
        if used + size > MAX_CONTEXT_BYTES:
            continue
        used += size
        context.append(entry)
        hits.append(candidate["hit"])
        if len(context) == MAX_ITEMS:
            break
    return hits, context
