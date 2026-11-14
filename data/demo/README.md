# Reviewed demo corpus

The reviewed [FlareLedger_NASA_Demo_Data.json](FlareLedger_NASA_Demo_Data.json) is included in this directory. It is approximately 13 MB. Its checksum and contents are recorded in [seed-reference.json](seed-reference.json).

Verify it from the repository root:

```bash
sha256sum data/demo/FlareLedger_NASA_Demo_Data.json
```

The expected hash is recorded in seed-reference.json. Preserve source and license records in future data PRs. A matching hash confirms file identity, not scientific correctness.

The source file includes ten investigations, nine original tables, six numerical series with 1,844 points, quality notes, and a download catalog. Matrix rows include notes and operating conditions. They are not all independent trials. Telemetry with unresolved units is separated from chart-ready series.

The seed format is flareledger.nasa_demo.v2. Project-authored explanations and labels use English, with localized field names ending in _en. Original numerical data and source payloads are unchanged.

The backend importer is still to be implemented. Do not treat copying this file as creating the SQLite database.
