"""Exercises the context query methods introduced on this branch.

Run:  cd python && python tests/test_all_methods.py
"""

from pathlib import Path
from pprint import pformat

from orgdatacore import Service
from orgdatacore._internal.testing import FileDataSource

TESTDATA = Path(__file__).parent.parent.parent / "testdata" / "test_org_data.json"
SEP = "-" * 60


def fmt(obj: object) -> str:
    s = pformat(obj, width=100)
    if "\n" in s:
        return "\n" + s
    return s


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def show(label: str, value: object) -> None:
    print(f"  {label}: {fmt(value)}")


def main() -> None:
    svc = Service()
    svc.load_from_data_source(FileDataSource(str(TESTDATA)))

    # --- GetContextForTeam / get_context_for_team ---
    section("get_context_for_team")
    show("platform-team", svc.get_context_for_team("platform-team"))
    show("test-team (no context)", svc.get_context_for_team("test-team"))
    show("nonexistent", svc.get_context_for_team("nonexistent"))

    # --- GetContextForEntity / get_context_for_entity ---
    section("get_context_for_entity")
    show("('platform-team', 'team')", svc.get_context_for_entity("platform-team", "team"))
    show("('test-org', 'org')", svc.get_context_for_entity("test-org", "org"))
    show("('platform-org', 'org') (no context)", svc.get_context_for_entity("platform-org", "org"))
    show("('engineering', 'pillar')", svc.get_context_for_entity("engineering", "pillar"))
    show("('backend-teams', 'team_group')", svc.get_context_for_entity("backend-teams", "team_group"))
    show("('nonexistent', 'team')", svc.get_context_for_entity("nonexistent", "team"))

    # --- GetContextByType / get_context_by_type ---
    section("get_context_by_type")
    show("('platform-team', 'release_framework', 'team')", svc.get_context_by_type("platform-team", "release_framework", "team"))
    show("('platform-team', 'team_onboarding', 'team')", svc.get_context_by_type("platform-team", "team_onboarding", "team"))
    show("('platform-team', 'code_review_standards', 'team')", svc.get_context_by_type("platform-team", "code_review_standards", "team"))
    show("('test-org', 'release_framework', 'org')", svc.get_context_by_type("test-org", "release_framework", "org"))
    show("('platform-team', 'nonexistent_type', 'team')", svc.get_context_by_type("platform-team", "nonexistent_type", "team"))
    show("('nonexistent', 'release_framework', 'team')", svc.get_context_by_type("nonexistent", "release_framework", "team"))

    # --- GetAllContextTypesForEntity / get_all_context_types_for_entity ---
    section("get_all_context_types_for_entity")
    show("('platform-team', 'team')", svc.get_all_context_types_for_entity("platform-team", "team"))
    show("('test-org', 'org')", svc.get_all_context_types_for_entity("test-org", "org"))
    show("('test-team', 'team') (no context)", svc.get_all_context_types_for_entity("test-team", "team"))
    show("('nonexistent', 'team')", svc.get_all_context_types_for_entity("nonexistent", "team"))

    # --- GetContextTypeDescriptions / get_context_type_descriptions ---
    section("get_context_type_descriptions")
    show("(from metadata)", svc.get_context_type_descriptions())

    # --- Empty service ---
    section("Empty Service (safe defaults)")
    empty = Service()
    show("get_context_for_team('x')", empty.get_context_for_team("x"))
    show("get_context_for_entity('x', 'team')", empty.get_context_for_entity("x", "team"))
    show("get_context_by_type('x', 'y', 'team')", empty.get_context_by_type("x", "y", "team"))
    show("get_all_context_types_for_entity('x', 'team')", empty.get_all_context_types_for_entity("x", "team"))
    show("get_context_type_descriptions()", empty.get_context_type_descriptions())

    print(f"\n{SEP}")
    print("  Done — all context methods exercised.")
    print(SEP)


if __name__ == "__main__":
    main()
