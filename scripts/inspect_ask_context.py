"""Inspect all frozen questions against local retrieval; never contact a provider.

Run with the backend Python 3.12 environment. Only an isolated temporary corpus
database is imported. Existing evaluation receipts and quota state are not opened.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED_SHA = "90be248ab23b24f6eaa51e3923ba5937631493630fd4833e18a2dbb51897bc52"
FIXTURE_SHA = "4cf749bc5216feb92b55b05294b9ee1ad021a625ae51992c6ad7fb14a269f299"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pointer(value: object, path: str) -> object:
    for token in path.strip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]  # type: ignore[index]
    return value


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def audit() -> tuple[dict, list[dict]]:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.config import Settings
    from app.ingest import import_corpus
    from app.llm import LLMSettings, request_payload
    from app.retrieval import retrieve
    from app.storage import Repository

    seed_path = ROOT / "data/demo/FlareLedger_NASA_Demo_Data.json"
    fixture_path = ROOT / "docs/ai-evaluation-cases.json"
    if sha(seed_path) != SEED_SHA or sha(fixture_path) != FIXTURE_SHA:
        raise ValueError("Frozen seed or evaluation fixture differs; inspection stopped.")
    seed, fixture = json.loads(seed_path.read_text()), json.loads(fixture_path.read_text())
    anchor_count = 0
    for case in fixture["cases"]:
        for anchor in case["anchors"]:
            actual = pointer(seed, anchor["seed_pointer"])
            expected = anchor["expected"]
            matched = actual == expected if anchor["check"] == "equals" else expected in actual
            if not matched:
                raise ValueError("Frozen evidence anchor differs: " + case["id"] + anchor["seed_pointer"])
            anchor_count += 1
    selections = []
    with tempfile.TemporaryDirectory(prefix="flareledger-retrieval-inspection-") as directory:
        settings = Settings(Path(directory) / "inspection.sqlite3", ROOT / "data")
        import_corpus(settings)
        repository = Repository(settings)
        before = sha(settings.database_path)
        for case in fixture["cases"]:
            with repository.connection() as db:
                hits, context = retrieve(repository, db, case["question"])
            context_bytes = len(json.dumps(context).encode())
            payload = request_payload(LLMSettings(), case["question"], context)
            request_bytes = len(json.dumps(payload).encode())
            if len(context) > 5 or context_bytes > 16000 or request_bytes > 32768:
                raise ValueError("Context/request bound exceeded: " + case["id"])
            selected_sources = {source for item in context for source in item["source_ids"]}
            selections.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "required_facts": case["required_facts"],
                    "forbidden_claims": case["forbidden_claims"],
                    "context_requirement": case["context_requirement"],
                    "review_source_ids": case["review_source_ids"],
                    "selected_source_ids": sorted(selected_sources),
                    "review_source_ids_not_selected": sorted(
                        set(case["review_source_ids"]) - selected_sources
                    ),
                    "source_id_coverage_is_not_a_sufficiency_grade": True,
                    "selected_ids": [hit["id"] for hit in hits],
                    "context_bytes": context_bytes,
                    "request_bytes": request_bytes,
                    "context": context,
                    "live_result": "NOT_RUN_BY_THIS_INSPECTION",
                    "scientific_grade": "NOT_GRADED",
                }
            )
        unchanged = before == sha(settings.database_path)
        if not unchanged:
            raise ValueError("Retrieval modified the temporary database.")
    by_id = {
        row["id"]: {item["id"]: json.loads(item["support_text"]) for item in row["context"]}
        for row in selections
    }
    materials = by_id["AE-01"]
    material_tables = all(
        any("pmma" in " ".join(row["cells_as_reported"]).casefold() for row in materials[source]["rows"])
        for source in ("SRC-TABLE-PSI-25", "SRC-TABLE-PSI-26")
        if source in materials
    ) and all(source in materials for source in ("SRC-TABLE-PSI-25", "SRC-TABLE-PSI-26"))
    readme = " ".join(p["text"] for p in materials.get("SRC-README-PSI-25", {}).get("paragraphs", []))
    same = by_id["AE-12"].get("SRC-TABLE-PSI-102", {})
    historical = by_id["AE-13"]
    checks = {
        "AE-01_original_material_cells_from_both_tables": material_tables,
        "AE-01_verified_readme_films_slabs_rods": all(
            word in readme.casefold() for word in ("films", "slabs", "rods")
        ),
        "AE-12_complete_condition_definitions_and_references": same.get("all_rows_included") is True
        and len(same.get("rows", [])) == 8
        and [row["normalized_record_type"] for row in same["rows"]]
        == ["condition_definition"] * 4 + ["condition_reference"] * 4,
        "AE-13_both_historical_cards": {"CARD-SRC-APOLLO-1", "CARD-SRC-MIR-FIRE"} <= historical.keys(),
        "AE-15_no_context_selected": not by_id["AE-15"],
    }
    if not all(checks.values()):
        raise ValueError("A targeted retrieval regression is unresolved: " + json.dumps(checks))
    identity = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "local_commit": git("rev-parse", "HEAD"),
        "local_tree": git("rev-parse", "HEAD^{tree}"),
        "tracked_worktree_dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        "seed_sha256": SEED_SHA,
        "fixture_sha256": FIXTURE_SHA,
        "model_calls": 0,
        "http_requests": 0,
        "quota_state_opened": False,
        "temporary_database_unchanged": unchanged,
        "cases_inspected": len(selections),
        "seed_anchors_matched": anchor_count,
        "max_request_bytes": max(row["request_bytes"] for row in selections),
        "retrieval_regressions": checks,
        "scientific_grades_assigned": 0,
        "interpretation": "Offline evidence-selection checks only; no live answer, scientific acceptance score, or deployment assertion.",
        "limits": [
            "Large original tables and documents are sampled; absence from a packet does not establish absence from the full source.",
            "Series points are not sent. Curve calculations and unmeasured quantities remain unsupported.",
            "Exact excerpts of project annotations are not original NASA quotations. Context/source membership does not establish entailment or source-specific provenance.",
            "Fresh live evaluation needs the deployed reviewed revision, operator preflight and separate receipts. Earlier results are not transferred to this revision.",
        ],
    }
    return identity, selections


def write_report(output: Path, identity: dict, selections: list[dict]) -> None:
    output.mkdir(parents=True)
    (output / "contexts").mkdir()
    for row in selections:
        (output / "contexts" / (row["id"] + ".json")).write_text(
            json.dumps(row, ensure_ascii=False, indent=2) + "\n"
        )
    (output / "IDENTITY.json").write_text(json.dumps(identity, indent=2) + "\n")
    summary = [
        {
            key: value
            for key, value in row.items()
            if key not in {"context", "required_facts", "forbidden_claims"}
        }
        for row in selections
    ]
    (output / "CONTEXT_REPORT.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    esc = html.escape
    rows = "".join(
        "<tr><td>"
        + esc(row["id"])
        + "</td><td>"
        + "<br>".join(esc(i) for i in row["selected_ids"])
        + "</td><td>"
        + str(row["request_bytes"])
        + "</td><td>Not graded</td></tr>"
        for row in selections
    )
    details = []
    for row in selections:
        facts = "".join("<li>" + esc(value) + "</li>" for value in row["required_facts"])
        forbidden = "".join("<li>" + esc(value) + "</li>" for value in row["forbidden_claims"])
        context = (
            "\n\n".join(
                item["id"] + "\n" + json.dumps(json.loads(item["support_text"]), ensure_ascii=False, indent=2)
                for item in row["context"]
            )
            or "No context selected."
        )
        details.append(
            "<details><summary>"
            + esc(row["id"] + " — " + row["question"])
            + "</summary><h3>Required facts</h3><ul>"
            + facts
            + "</ul><h3>Forbidden claims</h3><ul>"
            + forbidden
            + "</ul><p>"
            + esc(row["context_requirement"])
            + "</p><h3>Actual offline context</h3><pre>"
            + esc(context)
            + "</pre></details>"
        )
    checks = "".join(
        "<li>" + esc(key) + ": " + str(value) + "</li>"
        for key, value in identity["retrieval_regressions"].items()
    )
    page = (
        "<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>FlareLedger offline retrieval review</title><style>body{font:16px/1.6 system-ui;margin:32px auto;max-width:1120px;padding:0 20px;color:#173842;background:#f7f6ef}table{width:100%;border-collapse:collapse;background:white}td,th{padding:12px;border:1px solid #cdd8d2;text-align:left;overflow-wrap:anywhere}details{background:white;padding:16px;margin:16px 0;border:1px solid #cdd8d2;border-radius:6px}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 monospace;background:#f4f7f3;padding:16px}code{overflow-wrap:anywhere}.notice{padding:18px;background:#fff0d6;border:1px solid #e3c68c}</style><h1>FlareLedger: offline retrieval review</h1><p class=notice><strong>15 questions inspected. Zero HTTP/model requests. Zero scientific grades.</strong> This report does not submit Ask, modify earlier receipts or establish live answer quality. Required facts below are review criteria, never appended to provider input.</p><p>Code: <code>"
        + esc(identity["local_commit"])
        + "</code><br>Seed: <code>"
        + SEED_SHA
        + "</code></p><h2>Targeted retrieval regressions</h2><ul>"
        + checks
        + "</ul><p>All 45 frozen source anchors match the seed. Source-ID coverage alone is not proof of sufficient context. Large sources remain explicitly partial.</p><table><thead><tr><th>Case</th><th>Selected evidence</th><th>Request bytes / 32768</th><th>Scientific result</th></tr></thead><tbody>"
        + rows
        + "</tbody></table><h2>Review evidence</h2>"
        + "".join(details)
        + "<h2>Remaining limits</h2><ul>"
        + "".join("<li>" + esc(limit) + "</li>" for limit in identity["limits"])
        + "</ul></html>"
    )
    (output / "REVIEW_CARDS.html").write_text(page + "\n")
    files = sorted(path for path in output.rglob("*") if path.is_file())
    (output / "SHA256SUMS").write_text(
        "".join(sha(path) + "  " + path.relative_to(output).as_posix() + "\n" for path in files)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = args.output.expanduser().resolve()
        if output.exists():
            identity = json.loads((output / "IDENTITY.json").read_text())
            if identity["local_commit"] != git("rev-parse", "HEAD") or git(
                "status", "--porcelain", "--untracked-files=no"
            ):
                raise ValueError(
                    "Existing report has a different or modified code revision; use a new output directory."
                )
            for line in (output / "SHA256SUMS").read_text().splitlines():
                expected, name = line.split("  ", 1)
                path = (output / name).resolve()
                if not path.is_relative_to(output) or sha(path) != expected:
                    raise ValueError("Existing report integrity differs; it was preserved.")
            print("OFFLINE_REPORT_REUSED | " + str(output) + "; no HTTP/model requests.")
            return 0
        identity, selections = audit()
        write_report(output, identity, selections)
        print(
            "RETRIEVAL_OFFLINE_OK | 15 questions; 45/45 seed anchors; targeted regressions passed; 0 HTTP/model requests; 0 scientific grades."
        )
        print(str(output / "REVIEW_CARDS.html"))
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, "Inspection stopped: " + str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
