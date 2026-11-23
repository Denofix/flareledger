# Frontend dependency audit record

On 22 November 2026 a fresh full `npm audit --audit-level=moderate` returned exit code 0 with zero reported vulnerabilities on the committed frontend lockfile. The run used Node 24.22.3, npm 11.19.1, a fresh cache and the official npm registry.

GitHub withdrew the Picomatch advisory on 18 November 2026 after determining the reported behavior was outside its security scope. The lockfile still pins Picomatch 4.0.7. The full npm audit continues to run at the moderate threshold in CI. [GitHub advisory notice](https://github.com/advisories/GHSA-fc5q-39xc-vjpf)

## Historical failure on 17 November 2026

| Check | Result |
| --- | --- |
| `npm audit --omit=dev --audit-level=moderate` | Passed: zero reported production dependency vulnerabilities |
| `npm audit --audit-level=moderate` | Failed: 13 high-severity entries in one development dependency chain |
| Root package | `picomatch` 4.0.7, marked `dev: true` in package-lock.json |
| Advisory | [GHSA-fc5q-39xc-vjpf / CVE-2026-112366](https://github.com/advisories/GHSA-fc5q-39xc-vjpf) |

The 13 entries traced back to one advisory through development dependencies used for builds, linting, type checks and tests. CI runs those checks before the full audit so their results remain visible when a future advisory blocks it.
