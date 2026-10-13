"""Comprehensive PII redaction tests using real organizational data.

These tests load a real comprehensive index dump through the
RedactingDataSource and verify that ALL PII fields are properly
stripped from the in-memory index.
"""

import json
import os
from io import BytesIO

import pytest

from orgdatacore import PIIMode, RedactingDataSource, Service

COMPREHENSIVE_INDEX_PATH = os.path.expanduser(
    "~/comprehensive_index_dump.json"
)


class FileDataSource:
    """DataSource that reads from a file on disk."""

    def __init__(self, path: str) -> None:
        self._path = path

    def load(self) -> BytesIO:
        with open(self._path, "rb") as f:
            return BytesIO(f.read())

    def watch(self, callback):
        return None

    def __str__(self) -> str:
        return self._path


def _needs_comprehensive_index():
    return pytest.mark.skipif(
        not os.path.exists(COMPREHENSIVE_INDEX_PATH),
        reason=f"Comprehensive index not found at {COMPREHENSIVE_INDEX_PATH}",
    )


@pytest.fixture(scope="module")
def redacted_service() -> Service:
    """Load the comprehensive index through RedactingDataSource into a Service."""
    inner = FileDataSource(COMPREHENSIVE_INDEX_PATH)
    source = RedactingDataSource(inner, pii_mode=PIIMode.REDACTED)
    service = Service()
    service.load_from_data_source(source)
    return service


@pytest.fixture(scope="module")
def full_service() -> Service:
    """Load the comprehensive index in full mode (no redaction) for comparison."""
    inner = FileDataSource(COMPREHENSIVE_INDEX_PATH)
    source = RedactingDataSource(inner, pii_mode=PIIMode.FULL)
    service = Service()
    service.load_from_data_source(source)
    return service


@pytest.fixture(scope="module")
def redacted_raw() -> dict:
    """Load the comprehensive index through RedactingDataSource as raw JSON."""
    inner = FileDataSource(COMPREHENSIVE_INDEX_PATH)
    source = RedactingDataSource(inner, pii_mode=PIIMode.REDACTED)
    return json.load(source.load())


@pytest.fixture(scope="module")
def full_raw() -> dict:
    """Load the comprehensive index in full mode as raw JSON."""
    inner = FileDataSource(COMPREHENSIVE_INDEX_PATH)
    source = RedactingDataSource(inner, pii_mode=PIIMode.FULL)
    return json.load(source.load())


@_needs_comprehensive_index()
class TestEmployeePIIRedaction:
    """Verify all employee PII fields are redacted."""

    def test_all_full_names_redacted(self, redacted_raw: dict) -> None:
        employees = redacted_raw["lookups"]["employees"]
        assert len(employees) > 0, "No employees found"
        for uid, emp in employees.items():
            assert emp["full_name"] == "[REDACTED]", (
                f"Employee {uid}: full_name not redacted: {emp['full_name']}"
            )

    def test_all_emails_redacted(self, redacted_raw: dict) -> None:
        employees = redacted_raw["lookups"]["employees"]
        for uid, emp in employees.items():
            assert emp["email"] == "[REDACTED]", (
                f"Employee {uid}: email not redacted: {emp['email']}"
            )

    def test_all_slack_uids_cleared(self, redacted_raw: dict) -> None:
        employees = redacted_raw["lookups"]["employees"]
        for uid, emp in employees.items():
            slack = emp.get("slack_uid")
            assert slack is None or slack == "", (
                f"Employee {uid}: slack_uid not cleared: {slack}"
            )

    def test_all_github_ids_cleared(self, redacted_raw: dict) -> None:
        employees = redacted_raw["lookups"]["employees"]
        for uid, emp in employees.items():
            gh = emp.get("github_id")
            assert gh is None or gh == "", (
                f"Employee {uid}: github_id not cleared: {gh}"
            )


@_needs_comprehensive_index()
class TestNonPIIPreserved:
    """Verify non-PII employee fields are preserved."""

    def test_uids_preserved(self, redacted_raw: dict) -> None:
        employees = redacted_raw["lookups"]["employees"]
        for uid, emp in employees.items():
            assert emp["uid"] == uid, f"Employee {uid}: uid mismatch"

    def test_job_titles_preserved(self, redacted_raw: dict, full_raw: dict) -> None:
        redacted_emps = redacted_raw["lookups"]["employees"]
        full_emps = full_raw["lookups"]["employees"]
        for uid in list(full_emps.keys())[:50]:
            assert redacted_emps[uid]["job_title"] == full_emps[uid]["job_title"], (
                f"Employee {uid}: job_title changed"
            )

    def test_manager_uids_preserved(self, redacted_raw: dict, full_raw: dict) -> None:
        redacted_emps = redacted_raw["lookups"]["employees"]
        full_emps = full_raw["lookups"]["employees"]
        for uid in list(full_emps.keys())[:50]:
            assert redacted_emps[uid].get("manager_uid") == full_emps[uid].get("manager_uid"), (
                f"Employee {uid}: manager_uid changed"
            )

    def test_employee_count_unchanged(self, redacted_raw: dict, full_raw: dict) -> None:
        assert len(redacted_raw["lookups"]["employees"]) == len(full_raw["lookups"]["employees"])


@_needs_comprehensive_index()
class TestIndexRedaction:
    """Verify PII-containing indexes are cleared."""

    def test_slack_uid_to_uid_empty(self, redacted_raw: dict) -> None:
        slack_index = redacted_raw["indexes"]["slack_id_mappings"]["slack_uid_to_uid"]
        assert slack_index == {}, (
            f"slack_uid_to_uid should be empty, got {len(slack_index)} entries"
        )

    def test_github_id_to_uid_empty(self, redacted_raw: dict) -> None:
        github_index = redacted_raw["indexes"]["github_id_mappings"]["github_id_to_uid"]
        assert github_index == {}, (
            f"github_id_to_uid should be empty, got {len(github_index)} entries"
        )

    def test_full_mode_slack_index_populated(self, full_raw: dict) -> None:
        slack_index = full_raw["indexes"]["slack_id_mappings"]["slack_uid_to_uid"]
        assert len(slack_index) > 0, "Expected non-empty slack index in full mode"

    def test_full_mode_github_index_populated(self, full_raw: dict) -> None:
        github_index = full_raw["indexes"]["github_id_mappings"]["github_id_to_uid"]
        assert len(github_index) > 0, "Expected non-empty github index in full mode"


@_needs_comprehensive_index()
class TestNonPIIIndexesPreserved:
    """Verify non-PII indexes are preserved after redaction."""

    def test_membership_index_preserved(self, redacted_raw: dict, full_raw: dict) -> None:
        redacted_membership = redacted_raw["indexes"]["membership"]["membership_index"]
        full_membership = full_raw["indexes"]["membership"]["membership_index"]
        assert len(redacted_membership) == len(full_membership), (
            "Membership index size changed after redaction"
        )

    def test_component_ownership_preserved(self, redacted_raw: dict, full_raw: dict) -> None:
        redacted_co = redacted_raw["indexes"].get("component_ownership", {})
        full_co = full_raw["indexes"].get("component_ownership", {})
        assert len(redacted_co) == len(full_co), (
            "Component ownership index size changed after redaction"
        )

    def test_jira_index_preserved(self, redacted_raw: dict, full_raw: dict) -> None:
        redacted_jira = redacted_raw["indexes"].get("jira", {})
        full_jira = full_raw["indexes"].get("jira", {})
        assert len(redacted_jira) == len(full_jira), (
            "Jira index size changed after redaction"
        )


@_needs_comprehensive_index()
class TestEscalationContactRedaction:
    """Verify escalation contacts in groups are redacted."""

    def _check_entity_escalation(self, entities: dict, entity_type: str) -> None:
        for name, entity in entities.items():
            group = entity.get("group", {})
            for i, contact in enumerate(group.get("escalation", [])):
                assert contact["name"] == "[REDACTED]", (
                    f"{entity_type}/{name} escalation[{i}] name not redacted: {contact['name']}"
                )
                assert contact.get("url", "") == "", (
                    f"{entity_type}/{name} escalation[{i}] url not cleared"
                )
                assert contact["description"] == "[REDACTED]", (
                    f"{entity_type}/{name} escalation[{i}] description not redacted"
                )

    def test_team_escalation_redacted(self, redacted_raw: dict) -> None:
        self._check_entity_escalation(
            redacted_raw["lookups"].get("teams", {}), "team"
        )

    def test_org_escalation_redacted(self, redacted_raw: dict) -> None:
        self._check_entity_escalation(
            redacted_raw["lookups"].get("orgs", {}), "org"
        )

    def test_pillar_escalation_redacted(self, redacted_raw: dict) -> None:
        self._check_entity_escalation(
            redacted_raw["lookups"].get("pillars", {}), "pillar"
        )

    def test_team_group_escalation_redacted(self, redacted_raw: dict) -> None:
        self._check_entity_escalation(
            redacted_raw["lookups"].get("team_groups", {}), "team_group"
        )

    def test_escalation_contacts_exist_in_full_mode(self, full_raw: dict) -> None:
        """Sanity check: at least some teams should have escalation contacts."""
        has_escalation = False
        for team in full_raw["lookups"].get("teams", {}).values():
            if team.get("group", {}).get("escalation"):
                has_escalation = True
                break
        assert has_escalation, "No escalation contacts found in full mode data"


@_needs_comprehensive_index()
class TestServiceIntegration:
    """Test that the Service works correctly with redacted data."""

    def test_employee_lookup_returns_redacted(self, redacted_service: Service, full_raw: dict) -> None:
        uids = list(full_raw["lookups"]["employees"].keys())[:10]
        for uid in uids:
            emp = redacted_service.get_employee_by_uid(uid)
            assert emp is not None, f"Employee {uid} not found"
            assert emp.full_name == "[REDACTED]"
            assert emp.email == "[REDACTED]"
            assert emp.slack_uid == ""
            assert emp.github_id == ""

    def test_slack_lookup_returns_none(self, redacted_service: Service, full_raw: dict) -> None:
        slack_ids = list(full_raw["indexes"]["slack_id_mappings"]["slack_uid_to_uid"].keys())[:10]
        for slack_id in slack_ids:
            emp = redacted_service.get_employee_by_slack_id(slack_id)
            assert emp is None, f"Slack lookup for {slack_id} should return None in redacted mode"

    def test_github_lookup_returns_none(self, redacted_service: Service, full_raw: dict) -> None:
        github_ids = list(full_raw["indexes"]["github_id_mappings"]["github_id_to_uid"].keys())[:10]
        for github_id in github_ids:
            emp = redacted_service.get_employee_by_github_id(github_id)
            assert emp is None, f"GitHub lookup for {github_id} should return None in redacted mode"

    def test_uid_lookup_still_works(self, redacted_service: Service, full_raw: dict) -> None:
        """UID lookups should still work (UIDs are not PII)."""
        uids = list(full_raw["lookups"]["employees"].keys())[:20]
        for uid in uids:
            emp = redacted_service.get_employee_by_uid(uid)
            assert emp is not None, f"Employee {uid} should be findable by UID"
            assert emp.uid == uid

    def test_team_queries_still_work(self, redacted_service: Service, full_raw: dict) -> None:
        """Team queries should still work with redacted data."""
        team_names = list(full_raw["lookups"].get("teams", {}).keys())[:10]
        for name in team_names:
            team = redacted_service.get_team_by_name(name)
            assert team is not None, f"Team {name} should be found"
            assert team.name == name

    def test_membership_queries_still_work(self, redacted_service: Service, full_raw: dict) -> None:
        """Membership queries should still work with redacted data."""
        membership = full_raw["indexes"]["membership"]["membership_index"]
        uids_with_membership = [
            uid for uid, memberships in membership.items() if memberships
        ][:10]
        for uid in uids_with_membership:
            teams = redacted_service.get_teams_for_uid(uid)
            # We just check it doesn't crash; the result should be a list
            assert isinstance(teams, list)
