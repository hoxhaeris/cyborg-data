"""Tests for canonical pydantic model validation and serialization behavior.

Validates that the canonical orgindex-schema models (re-exported by orgdatacore)
correctly handle JSON parsing, defaults, nested shapes, and round-trips.
"""

import pytest
from pydantic import ValidationError

from orgdatacore._service import _parse_employee
from orgdatacore._types import (
    Component,
    Employee,
    Group,
    GroupType,
    RepoInfo,
    RoleInfo,
    Team,
)


class TestModelValidate:
    """Tests for Model.model_validate() (JSON dict -> model)."""

    def test_employee_full_data(self):
        data = {
            "uid": "jsmith",
            "full_name": "John Smith",
            "email": "jsmith@example.com",
            "job_title": "Engineer",
            "slack_uid": "U123",
            "github_id": "jsmith-gh",
            "manager_uid": "mgr1",
            "timezone": "US/Eastern",
        }
        emp = Employee.model_validate(data)
        assert emp.uid == "jsmith"
        assert emp.full_name == "John Smith"
        assert emp.email == "jsmith@example.com"
        assert emp.github_id == "jsmith-gh"

    def test_employee_missing_fields_uses_defaults(self):
        emp = Employee.model_validate({"uid": "x"})
        assert emp.uid == "x"
        assert emp.full_name == ""

    def test_employee_empty_dict(self):
        emp = Employee.model_validate({})
        assert emp.uid == ""

    def test_nested_model_validation(self):
        data = {
            "name": "Team One",
            "group": {
                "type": {"name": "dev"},
                "resolved_people_uid_list": ["a", "b"],
            },
        }
        team = Team.model_validate(data)
        assert team.group is not None
        assert team.group.type is not None
        assert team.group.type.name == "dev"
        assert team.group.resolved_people_uid_list == ["a", "b"]


class TestEmployeeNullCoercion:
    """Null string fields on an employee record coerce to "".

    Go's json.Unmarshal leaves a null string field as "" and loads the index
    successfully. The Python consumer must match that: a null uid/full_name/etc.
    must not raise a ValidationError and abort the entire load.
    """

    @pytest.mark.parametrize(
        "field",
        [
            "uid",
            "full_name",
            "email",
            "job_title",
            "github_id",
            "manager_uid",
            "slack_uid",
            "timezone",
        ],
    )
    def test_null_string_field_coerced_to_empty(self, field: str):
        emp = _parse_employee({"uid": "u1", "full_name": "Name", field: None})
        assert getattr(emp, field) == ""

    def test_null_possible_github_ids_coerced_to_empty_list(self):
        """A null possible_github_ids (Go nil slice) must coerce to [], not abort load."""
        emp = _parse_employee({"uid": "u1", "possible_github_ids": None})
        assert emp.possible_github_ids == []

    def test_all_null_strings_at_once(self):
        emp = _parse_employee(
            {
                "uid": None,
                "full_name": None,
                "email": None,
                "job_title": None,
                "github_id": None,
                "manager_uid": None,
                "slack_uid": None,
                "timezone": None,
            }
        )
        assert emp.uid == ""
        assert emp.full_name == ""
        assert emp.email == ""


class TestLeafFields:
    """Tests for leaf model field names (canonical on-disk names, no aliases)."""

    def test_repo_info_uses_repo_name(self):
        """The on-disk key is repo_name (not repo)."""
        repo = RepoInfo.model_validate(
            {"repo_name": "my-repo", "description": "A repo"}
        )
        assert repo.repo_name == "my-repo"
        assert repo.description == "A repo"

    def test_group_uses_resolved_roles(self):
        """The group's role list is resolved_roles (not roles)."""
        group = Group.model_validate(
            {
                "type": {"name": "dev"},
                "resolved_people_uid_list": [],
                "resolved_roles": [
                    {"people": ["u1"], "roles": ["lead"], "description": ""}
                ],
            }
        )
        assert len(group.resolved_roles) == 1
        assert group.resolved_roles[0].people == ["u1"]


class TestModelDump:
    """Tests for model_dump() (model -> dict)."""

    def test_repo_info_dump(self):
        repo = RepoInfo(repo_name="my-repo", description="desc")
        d = repo.model_dump()
        assert d["repo_name"] == "my-repo"
        assert "repo" not in d

    def test_group_dump_has_resolved_roles(self):
        group = Group(
            type=GroupType(name="dev"),
            resolved_roles=[RoleInfo(people=["u1"], roles=["lead"])],
        )
        d = group.model_dump()
        assert "resolved_roles" in d
        assert "roles" not in d


class TestComponentValidation:
    """Tests for the canonical nested Component shape."""

    def test_nested_component(self):
        data = {
            "name": "comp2",
            "description": "a component",
            "repos_list": ["repo-a"],
            "component": {
                "type": {"name": "service"},
                "repos": [{"repo_name": "r2"}],
                "jiras": [{"project": "PROJ", "component": "c1"}],
            },
        }
        comp = Component.model_validate(data)
        assert comp.name == "comp2"
        assert comp.repos_list == ["repo-a"]
        assert comp.component is not None
        assert comp.component.type is not None
        assert comp.component.type.name == "service"
        assert len(comp.component.repos) == 1
        assert comp.component.repos[0].repo_name == "r2"
        assert len(comp.component.jiras) == 1
        assert comp.component.jiras[0].project == "PROJ"

    def test_component_minimal(self):
        comp = Component.model_validate({"name": "comp1"})
        assert comp.name == "comp1"
        assert comp.component is None


class TestRoundTrip:
    """Tests for validate -> dump -> validate round-trip."""

    def test_employee_round_trip(self):
        data = {
            "uid": "jsmith",
            "full_name": "John Smith",
            "email": "j@x.com",
            "job_title": "Eng",
            "slack_uid": "U1",
            "github_id": "gh1",
        }
        emp = Employee.model_validate(data)
        dumped = emp.model_dump()
        emp2 = Employee.model_validate(dumped)
        assert emp == emp2

    def test_team_round_trip(self):
        data = {
            "name": "Team",
            "group": {
                "type": {"name": "dev"},
                "resolved_people_uid_list": ["a"],
                "resolved_roles": [
                    {"people": ["a"], "roles": ["lead"], "description": ""}
                ],
                "repos": [{"repo_name": "r1", "description": ""}],
                "jiras": [{"project": "P", "component": "C"}],
            },
            "parent": {"name": "org1", "type": "org"},
        }
        team = Team.model_validate(data)
        dumped = team.model_dump()
        team2 = Team.model_validate(dumped)
        assert team == team2


class TestFrozenModels:
    """Tests for frozen model immutability."""

    def test_employee_is_frozen(self):
        emp = Employee(uid="x")
        with pytest.raises(ValidationError):
            emp.uid = "y"  # type: ignore[misc]
        assert emp.uid == "x"

    def test_model_copy_creates_new_instance(self):
        emp = Employee(uid="x", full_name="Original")
        emp2 = emp.model_copy(update={"full_name": "Updated"})
        assert emp.full_name == "Original"
        assert emp2.full_name == "Updated"
        assert emp.uid == emp2.uid
