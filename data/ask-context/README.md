# Hash-pinned source companion for Ask

The numerical seed and its hash are unchanged. This directory resolves an
already registered original source file that the seed previously described by
metadata and a download link without embedding its text.

| Field | Recorded value |
| --- | --- |
| Source ID | `SRC-README-PSI-25` |
| Original filename | `PSI-25_Science Documents_BASS-II_ReadMe.docx` |
| NASA file ID / version | `692480587f6aa6a830210602` / `2` |
| Original bytes | `21538` |
| SHA256 / local filename | `69f32647792f54ab2a561e3cdafc6c87d854564fe487aed2b09265286bd84e1d.docx` |
| License recorded in the seed | `CC0-1.0`, basis `SRC-PSI-25` |

[Registered NASA download URL](https://psi.nasa.gov/geode-py/ws/studies/PSI-25/download?file=692480587f6aa6a830210602&version=2&redirect=false).
The retained original file matches both the byte count and SHA256 recorded in
the frozen seed. On 15 November 2026 an attempted new download returned HTML;
that HTML was rejected, and the matching retained original snapshot was used.
This does not establish current availability of the upstream download route.

The runtime verifies the original bytes against the installed source metadata,
then reads only `word/document.xml` using standard-library ZIP/XML parsing with
size bounds. It preserves Word text, tab and line-break nodes within each
paragraph, retains original paragraph numbers (including empty paragraphs), and
selects complete relevant paragraphs. It never downloads a document during Ask.
The context explicitly states that selected paragraphs are a subset. Missing,
changed or invalid bytes are omitted, never replaced by a generated summary.

Docker Compose already mounts `data/` read-only. Deploy this reviewed companion
with the same checkout/data mount as the API image. Native Python uses the same
`DATA_DIR` convention. No database migration or quota reset is needed; restoring
a database alone does not install this companion. Keep it with the reviewed code
for reproducible recovery and record both the code SHA and corpus version.

The root MIT license does not relicense this source. Bibliographic references
inside the original document do not grant rights to reproduce the referenced
third-party articles or media. See [data licenses](../../DATA_LICENSES.md).
