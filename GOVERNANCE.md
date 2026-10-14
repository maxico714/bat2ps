# Governance (light)

bat2ps is maintained by volunteers. Decisions are made by lazy consensus
among maintainers; contentious changes (profile bumps, dependency adds,
releases) require an ADR in `docs/adr/` and a 72-hour review window.

- **Maintainers:** listed in `.github/CODEOWNERS`. New maintainers are
  added after 3 merged PRs and a maintainer nomination.
- **Releases:** SemVer + Keep a Changelog; tags only from `main` with
  green CI; registry publishing needs a second maintainer's approval
  (G3 gate) via trusted publishing (OIDC).
- **Profile changes** (`profiles/*.yaml`, `docs/BATCH_PROFILE.md`) are
  minor-version bumps with migration notes; emitter/harness bug fixes
  are patches.
