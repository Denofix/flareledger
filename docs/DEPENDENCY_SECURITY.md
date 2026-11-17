# Frontend dependency advisory

Checked on 17 November 2026 against the committed frontend lockfile. This is a specific dependency finding, not a complete application security audit.

| Check | Result |
| --- | --- |
| `npm audit --omit=dev --audit-level=moderate` | Passed: zero reported production dependency vulnerabilities |
| `npm audit --audit-level=moderate` | Failed: 13 high-severity entries in one development dependency chain |
| Root package | `picomatch` 4.0.7, marked `dev: true` in package-lock.json |
| Advisory | [GHSA-fc5q-39xc-vjpf / CVE-2026-112366](https://github.com/advisories/GHSA-fc5q-39xc-vjpf) |
| Published package version | `npm view picomatch version dist-tags --json` returned 4.0.7 as latest |

The advisory concerns repeated extglob patterns that can cause excessive regular-expression backtracking. The 13 audit entries include dependent build, lint, typecheck and test packages; they are not 13 unrelated vulnerabilities. The deployed frontend is static, and the API is Python, but a clean production-only audit does not resolve the development-tooling finding.

At inspection, no newer patched package release was available in the registry, consistent with the [upstream release list](https://github.com/micromatch/picomatch/releases). The audit's suggested forced downgrade of Vitest is not evidence that the underlying Picomatch issue would be fixed.

## Release handling

- The full audit remains blocking in CI. Its threshold is not lowered and the advisory is not ignored.
- Behavioral checks and the production build now run before that audit, so their results remain visible even when the dependency gate fails.
- Use the documented loopback-only development command and trusted source/configuration. Do not expose a Vite development server as production hosting or evaluate untrusted glob patterns.
- Before merging a release, obtain a verified upstream fix or a separately reviewed, tested mitigation and rerun installation, audit, typecheck, lint, tests and build.
- Keep this finding open until evidence establishes remediation. Do not describe the current repository as having a fully clean dependency audit.

The flame/sidebar changes do not modify package versions, install hooks or the lockfile. No unreviewed dependency patch or framework downgrade is included.
