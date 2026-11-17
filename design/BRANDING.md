# FlareLedger branding provenance

## Active identity

On 17 November 2026, the project owner requested the original flame identity again. The favicon is restored byte-for-byte from commit `969cb9460de9115fe0a16016bd02bf168aa7175e`, file `frontend/public/favicon.svg`. Both standalone mark exports use those same bytes. The horizontal exports pair the original flame with the FlareLedger wordmark and **RESEARCH, TRACEABLE.** in system fonts.

The application header, mobile header, browser favicon and README all use the flame. The former orbital F and its visible generation label are no longer served. No new image-generation request was used for this restoration. Assistance with code, documentation and SVG layout remains disclosed in [SI_USAGE.md](../SI_USAGE.md); this is not a claim that all project design was created without assistance.

**FlareLedger** is the product. **Proofonauts** is the two-person team: **Denys Voloshyn and Tymofii Chernoivanov**. No NASA insignia, flag or mission identifier is used as project branding.

## Previous identity and provenance

The SI-assisted orbital F supplied by Tymofii is retired, not relabelled as hand-drawn. The source-pack and served-file hashes remain under `previous_identity` in [branding-manifest.json](branding-manifest.json), and the original assets remain in Git history at `c0c8e69d4e066017ac8c275ed59830dfeef60f74`. They are not duplicated under the frontend's public directory.

The manifest records the active flame's source commit, exact original hash and every served asset hash. System fonts are resolved by the browser; no font file is bundled. Original scientific screenshot bytes and measurement data remain unchanged. See [asset credits](FRONTEND_ASSETS.md) and [DATA_LICENSES.md](../DATA_LICENSES.md).
