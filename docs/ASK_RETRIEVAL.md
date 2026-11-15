# Bounded Ask evidence retrieval

The retriever uses local lexical matching and explicit corpus identifiers; it
does not call a model, embed text, query a vector database, browse the web or
write corpus/quota state. Search retains its existing independent AND-keyword
contract. Ask's public response fields and `lexical_keywords` method label stay
compatible.

The previous selector could fill its five slots with investigation summaries,
file metadata or broad matches. PMMA material cells, SAME condition definitions
and the named Mir historical card could be omitted even though the corpus
contained them. `app.retrieval` now:

- considers up to 32 significant query words, including scientific qualifiers,
  with word boundaries, simple plural forms and camel-case file/quantity names;
- scopes explicit investigation IDs/acronyms and named measured trials, prioritizes
  explicitly named or distinctive historical cards, and keeps broad matches from
  displacing the requested entities;
- supplies source packets with complete headers and original raw row cells.
  Tables of at most 12 rows are included completely. Larger tables select up to
  three rows for diverse query-term/qualifier coverage and include referenced
  definition rows when present. Original row numbers, source/file version,
  hash, total count and normalized record types are retained. A subset is marked
  explicitly and must not be treated as a complete table or independent-run count;
- adds complete small embedded TestSheets and the headers of large raw text
  series files for an explicitly named trial, without relabeling measurements,
  changing units or sending full series points;
- resolves the [hash-pinned BASS-II ReadMe](../data/ask-context/README.md) locally
  and selects complete numbered paragraphs. This is an original source companion,
  not a change to the frozen numerical seed.

Limits remain five context items, 5,000 UTF-8 bytes per support text, 16,000 bytes
of context entry accounting and 32,768 bytes per complete provider request. An
oversized item is omitted rather than silently truncating its numbers or quote.
Historical context, normalized metadata, project annotations and original cells
or document text have distinct basis labels. The provider's claim-bound schema
and final strict validator remain in force; see [AI setup](AI_SETUP.md).

## Offline inspection

Using the existing Python 3.12 backend environment, from the repository root:

```bash
backend/.venv/bin/python scripts/inspect_ask_context.py --output /absolute/path/to/a/new/offline-report
```

A separate worktree can use the original checkout's absolute virtualenv path.
The inspector imports the checksum-pinned seed into a temporary database, checks
all 45 frozen anchors, runs all 15 exact questions through local retrieval and
checks request-size bounds using the adapter's pure request builder. It never
calls the provider. It records the actual code commit, seed/fixture hashes,
selected IDs, complete supplied context and targeted retrieval regressions.
Read `REVIEW_CARDS.html`, `IDENTITY.json`, `CONTEXT_REPORT.json` and per-case JSON.
An existing intact report for the same clean commit is reused; a conflicting
report is preserved and rejected.

Source-ID coverage and targeted fragment checks are navigation/regression checks,
not scientific grades. The original live evaluation directory and receipts are
not read or changed. No live answer is imported, promoted to PASS or transferred
between revisions. A later live case needs the deployed reviewed SHA, fresh
operator preflight and a new separate receipt.

## Remaining limits

Large tables/documents remain partial, and the ranker is lexical. A selected
source does not prove that every required fact was sent. Curve calculations,
unknown time-zero events, uncertainty and unmeasured safety thresholds remain
unsupported. Mechanical context membership, exact excerpts and numeric-token
checks do not prove entailment, number/unit binding or source-specific provenance.
The model can still choose an inappropriate attached source for an authored
annotation; independent review of the actual answer and original file is needed.

The 15-case set was used to investigate these retrieval gaps and is not a held-out
benchmark. Variant-wording regression tests check general selection behavior;
new independent review questions are still required before a scientific readiness
claim. The runtime does not read evaluation questions, expectations or case IDs.
