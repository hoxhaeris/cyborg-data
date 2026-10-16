# Changelog

All notable changes to the `orgdatacore` Python package are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [2.0.0] — unreleased

Adopt the canonical [`orgindex-schema`](https://github.com/openshift-eng/orgindex-schema)
models as the single source of truth for the on-disk index shape (OCPCRT-658).
This is a breaking change to the **model shape**; the query-method API and load
behavior are unchanged (verified against a real production index — cross-branch
differential test: 36,348 cases, 0 mismatches).

### Added
- `orgindex-schema` is now a **required** dependency (pinned to `v0.1.0`, a public
  git source). It is pulled in automatically by pip/uv when installing
  `orgdatacore`; no manual install is needed. (Note: installation now requires
  network access to GitHub.)
- `Employee.possible_github_ids` field (from the canonical schema).
- `cohorts` lookup collection on `Lookups`.
- PII redaction/anonymization now scrub `possible_github_ids` and also cover the
  `cohorts` collection.

### Changed
- On-disk index/entity models are re-exported from `orgindex-schema` under their
  historical names. `Team`/`Org`/`Pillar`/`TeamGroup` are now the single
  `HierarchyEntity`; `Component` is `ComponentEntry` with its detail nested under
  `.component`; `Data` is `ComprehensiveIndexModel`.
- Model collection fields are now `list` (previously `tuple`). Frozen models that
  hold populated list fields are therefore no longer hashable.
- `RepoInfo.repo` is now `repo_name`; the group role list is `resolved_roles`
  (previously `roles`).
- Serialization goes through `model_dump`, so cleared/empty optional fields are
  emitted as `""` / `[]` rather than omitted from the JSON.

### Removed
- `Employee.rhat_geo`, `Employee.cost_center`, `Employee.is_people_manager`
  (not present in real producer output).
- Top-level `uid`, `tab_name`, and `type` on hierarchy entities
  (`Team`/`Org`/`Pillar`/`TeamGroup`); identity is carried by `stable_id` /
  `parent_id`.
- `Metadata.total_teams`.
- The `JiraIndex` and `ComponentOwnershipIndex` exports (these indexes are bare
  maps, matching the Go `map` types).

### Migration notes
- Code that only **calls `Service` query methods** needs no changes.
- Code that reads the removed/renamed fields, imports `JiraIndex` /
  `ComponentOwnershipIndex`, relies on `tuple`-typed collections, or hashes model
  instances must be updated.

## [1.0.0]

Initial tracked release (pre-canonical models). Hand-maintained pydantic models
describing the on-disk index, consumed by `Service`.

[Unreleased]: https://github.com/openshift-eng/cyborg-data/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/openshift-eng/cyborg-data/compare/v1.0.0...v2.0.0
