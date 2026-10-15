"""Cross-branch differential integration harness for the Python consumer.

Runs the full public ``Service`` API over a single index and emits normalized
("semantic contract") results, or compares two such result files. Use it to prove
that a refactor (e.g. swapping model implementations) does not change observable
behavior: run it against two checkouts over the *same* index and compare.

The projection keeps only what a consumer actually reads (identities, names,
manager/membership relationships, hierarchy, jira/component ownership, context,
escalation) and deliberately drops intentionally-changed shape details so they do
not register as false regressions:

- Employee: rhat_geo / cost_center / is_people_manager (dropped) and
  possible_github_ids (added) are not compared.
- Hierarchy entities: top-level uid / type / tab_name are not compared.
- Component: flat-vs-nested internal shape is reduced to {name, description}.
- None and "" are treated as equal (canonical optional strings vs zero values).

Any remaining difference is a genuine behavioral regression.

Modes:
  diff_branches.py run <index.json> <out.json>
  diff_branches.py compare <main_results.json> <branch_results.json>

Typical workflow (compare `main` against the current branch over a real index):

  git worktree add /tmp/cyborg-main main
  cp parity/diff_branches.py /tmp/diff_branches.py          # identical file for both runs

  (cd python && uv run python /tmp/diff_branches.py run /path/index.json /tmp/branch.json)
  (cd /tmp/cyborg-main/python && uv run python /tmp/diff_branches.py run /path/index.json /tmp/main.json)

  (cd python && uv run python /tmp/diff_branches.py compare /tmp/main.json /tmp/branch.json)

  git worktree remove /tmp/cyborg-main

`compare` exits non-zero if any case mismatches or a case exists on only one side.
"""

import json
import sys
from typing import Any

from pydantic import BaseModel

# ---- class-name groups (old main names + new canonical names) ----
EMP = {"Employee", "EmployeeEntry"}
HIER = {"Team", "Org", "Pillar", "TeamGroup", "HierarchyEntity"}
COMP = {"Component", "ComponentEntry"}
PARENT = {"ParentInfo", "ParentRef"}
CTX = {"ContextItemInfo"}
ESC = {"EscalationContactInfo"}
PATH = {"HierarchyPathEntry"}
NODE = {"HierarchyNode"}
ORGINFO = {"OrgInfo"}
OWNERSHIP = {"ComponentOwnership"}
OWNER = {"ComponentOwnerInfo", "ComponentOwner"}
JIRA = {"JiraOwnerInfo", "JiraOwner"}
MEMB = {"MembershipInfo", "MembershipEntry"}


def g(o: Any, name: str, default: Any = None) -> Any:
    return getattr(o, name, default)


def project(m: Any) -> Any:
    """Project a model to the semantic contract shared by both branches."""
    t = type(m).__name__
    if t in EMP:
        return {
            "_t": "employee",
            "uid": g(m, "uid", ""),
            "full_name": g(m, "full_name", ""),
            "email": g(m, "email", ""),
            "job_title": g(m, "job_title", ""),
            "github_id": g(m, "github_id", ""),
            "manager_uid": g(m, "manager_uid", ""),
            "slack_uid": g(m, "slack_uid", ""),
            "timezone": g(m, "timezone", ""),
        }
    if t in HIER:
        grp = g(m, "group")
        parent = g(m, "parent")
        return {
            "_t": "hierarchy",
            "name": g(m, "name", ""),
            "description": g(m, "description", ""),
            "parent_name": g(parent, "name", "") if parent else "",
            "parent_id": g(m, "parent_id", ""),
            "stable_id": g(m, "stable_id", ""),
            "people": sorted(list(g(grp, "resolved_people_uid_list", []) or [])) if grp else [],
            "component_roles": sorted(list(g(grp, "component_roles", []) or [])) if grp else [],
        }
    if t in COMP:
        return {"_t": "component", "name": g(m, "name", ""), "description": g(m, "description", "")}
    if t in CTX:
        return {
            "_t": "ctx",
            "name": g(m, "name", ""),
            "types": sorted(list(g(m, "types", []) or [])),
            "description": g(m, "description", ""),
            "url": g(m, "url", ""),
            "owner": g(m, "owner", ""),
            "inheritance": g(m, "inheritance", ""),
            "source_entity": g(m, "source_entity", ""),
            "source_type": g(m, "source_type", ""),
        }
    if t in ESC:
        return {"_t": "esc", "name": g(m, "name", ""), "url": g(m, "url", ""), "description": g(m, "description", "")}
    if t in PATH:
        return {"_t": "path", "name": g(m, "name", ""), "type": g(m, "type", ""), "stable_id": g(m, "stable_id", "")}
    if t in NODE:
        return {
            "_t": "node",
            "name": g(m, "name", ""),
            "type": g(m, "type", ""),
            "stable_id": g(m, "stable_id", ""),
            "children": [project(c) for c in (g(m, "children", []) or [])],
        }
    if t in ORGINFO:
        return {"_t": "orginfo", "name": g(m, "name", ""), "type": g(m, "type", ""), "stable_id": g(m, "stable_id", "")}
    if t in OWNERSHIP:
        return {"_t": "ownership", "component": g(m, "component", ""), "ownership_types": sorted(list(g(m, "ownership_types", []) or []))}
    if t in OWNER:
        return {"_t": "owner", "name": g(m, "name", ""), "type": g(m, "type", ""), "ownership_types": sorted(list(g(m, "ownership_types", []) or []))}
    if t in JIRA:
        return {"_t": "jira", "name": g(m, "name", ""), "type": g(m, "type", "")}
    if t in MEMB:
        return {"_t": "memb", "name": g(m, "name", ""), "type": g(m, "type", ""), "stable_id": g(m, "stable_id", "")}
    if t in PARENT:
        return {"_t": "parent", "name": g(m, "name", ""), "type": g(m, "type", "")}
    return {"_t": "UNKNOWN:" + t, "repr": str(m)}


def norm(o: Any) -> Any:
    if o is None:
        return ""  # None == "" (canonical optional strings vs Go/old zero value)
    if isinstance(o, bool):
        return o
    if isinstance(o, (int, float, str)):
        return o
    if isinstance(o, BaseModel):
        return norm(project(o))
    if isinstance(o, (list, tuple)):
        return [norm(x) for x in o]
    if isinstance(o, dict):
        return {k: norm(v) for k, v in sorted(o.items())}
    return str(o)


def run(index_path: str, out_path: str) -> None:
    from orgdatacore import Service
    from orgdatacore._internal.testing.helpers import FakeDataSource

    raw = open(index_path).read()
    svc = Service()
    svc.load_from_data_source(FakeDataSource(data=raw))
    d = svc._data

    emp_uids = list(d.lookups.employees)
    slack_ids = sorted({g(e, "slack_uid") for e in d.lookups.employees.values() if g(e, "slack_uid")})
    github_ids = sorted({g(e, "github_id") for e in d.lookups.employees.values() if g(e, "github_id")})
    emails = sorted({g(e, "email") for e in d.lookups.employees.values() if g(e, "email")})
    teams = list(d.lookups.teams)
    orgs = list(d.lookups.orgs)
    pillars = list(d.lookups.pillars)
    tgs = list(d.lookups.team_groups)
    comps = list(d.lookups.components)
    # Use the public API for jira input generation (internal shape differs across
    # branches: bare dict vs JiraIndex wrapper).
    jira_projs = svc.get_jira_projects()
    jira_pairs = [(p, c) for p in jira_projs for c in svc.get_jira_components(p)]
    # slack channels from team group slack configs
    channels = set()
    for t in d.lookups.teams.values():
        grp = g(t, "group")
        sl = g(grp, "slack") if grp else None
        for ch in (g(sl, "channels", []) or []) if sl else []:
            if g(ch, "channel"):
                channels.add(g(ch, "channel"))
    channels = sorted(channels)

    results: dict[str, Any] = {}

    def rec(method: str, case: str, value: Any) -> None:
        results[f"{method}|{case}"] = norm(value)

    def safe(method: str, case: str, fn) -> None:
        try:
            rec(method, case, fn())
        except Exception as e:
            # Store only the exception type, not the message: identical error
            # behavior must compare equal even if wording differs across branches
            # (e.g. a ValidationError naming EmployeeEntry vs Employee).
            results[f"{method}|{case}"] = {"_error": type(e).__name__}

    # no-arg
    for m in [
        "get_all_employees", "get_all_teams", "get_all_orgs", "get_all_pillars",
        "get_all_team_groups", "get_all_components", "get_all_component_names",
        "get_all_employee_uids", "get_all_team_names", "get_all_org_names",
        "get_all_pillar_names", "get_all_team_group_names", "get_jira_projects",
        "get_context_type_descriptions",
    ]:
        safe(m, "-", getattr(svc, m))

    # per uid
    for u in emp_uids:
        safe("get_employee_by_uid", u, lambda u=u: svc.get_employee_by_uid(u))
        safe("get_manager_for_employee", u, lambda u=u: svc.get_manager_for_employee(u))
        safe("get_teams_for_uid", u, lambda u=u: svc.get_teams_for_uid(u))
        safe("get_user_memberships", u, lambda u=u: svc.get_user_memberships(u))
        safe("get_user_teams", u, lambda u=u: svc.get_user_teams(u))
    # per slack
    for s in slack_ids:
        safe("get_employee_by_slack_id", s, lambda s=s: svc.get_employee_by_slack_id(s))
        safe("get_teams_for_slack_id", s, lambda s=s: svc.get_teams_for_slack_id(s))
        safe("get_user_organizations", s, lambda s=s: svc.get_user_organizations(s))
    # per github / email
    for gh in github_ids:
        safe("get_employee_by_github_id", gh, lambda gh=gh: svc.get_employee_by_github_id(gh))
    for em in emails:
        safe("get_employee_by_email", em, lambda em=em: svc.get_employee_by_email(em))
    # per team
    for t in teams:
        safe("get_team_by_name", t, lambda t=t: svc.get_team_by_name(t))
        safe("get_team_members", t, lambda t=t: svc.get_team_members(t))
        safe("get_team_escalation", t, lambda t=t: svc.get_team_escalation(t))
        safe("get_components_for_team", t, lambda t=t: svc.get_components_for_team(t))
        safe("get_jira_ownership_for_team", t, lambda t=t: svc.get_jira_ownership_for_team(t))
        safe("get_context_for_team", t, lambda t=t: svc.get_context_for_team(t))
        safe("get_context_for_entity", t, lambda t=t: svc.get_context_for_entity(t, "team"))
        safe("get_all_context_types_for_entity", t, lambda t=t: svc.get_all_context_types_for_entity(t, "team"))
        safe("get_hierarchy_path.team", t, lambda t=t: svc.get_hierarchy_path(t, "team"))
        safe("get_descendants_tree.team", t, lambda t=t: svc.get_descendants_tree(t))
        for ct in (svc.get_all_context_types_for_entity(t, "team") or []):
            safe("get_context_by_type", f"{t}::{ct}", lambda t=t, ct=ct: svc.get_context_by_type(t, ct, "team"))
    # per org/pillar/tg
    for o in orgs:
        safe("get_org_by_name", o, lambda o=o: svc.get_org_by_name(o))
        safe("get_org_members", o, lambda o=o: svc.get_org_members(o))
        safe("get_hierarchy_path.org", o, lambda o=o: svc.get_hierarchy_path(o, "org"))
        safe("get_descendants_tree.org", o, lambda o=o: svc.get_descendants_tree(o))
    for p in pillars:
        safe("get_pillar_by_name", p, lambda p=p: svc.get_pillar_by_name(p))
        safe("get_descendants_tree.pillar", p, lambda p=p: svc.get_descendants_tree(p))
    for tgn in tgs:
        safe("get_team_group_by_name", tgn, lambda tgn=tgn: svc.get_team_group_by_name(tgn))
        safe("get_descendants_tree.tg", tgn, lambda tgn=tgn: svc.get_descendants_tree(tgn))
    # components
    for c in comps:
        safe("get_component_by_name", c, lambda c=c: svc.get_component_by_name(c))
        safe("get_teams_for_component", c, lambda c=c: svc.get_teams_for_component(c))
    # jira
    for p in jira_projs:
        safe("get_jira_components", p, lambda p=p: svc.get_jira_components(p))
        safe("get_teams_by_jira_project", p, lambda p=p: svc.get_teams_by_jira_project(p))
    for (p, c) in jira_pairs:
        safe("get_teams_by_jira_component", f"{p}::{c}", lambda p=p, c=c: svc.get_teams_by_jira_component(p, c))
    # slack channels
    for ch in channels:
        safe("get_teams_by_slack_channel", ch, lambda ch=ch: svc.get_teams_by_slack_channel(ch))
    safe("get_teams_by_slack_channel", "__none__", lambda: svc.get_teams_by_slack_channel("definitely-not-a-channel-xyz"))
    # pairwise booleans, derived from memberships
    for u in emp_uids:
        mem = svc.get_user_memberships(u)
        mteams = [g(x, "name") for x in mem if g(x, "type") == "team"]
        morgs = [g(x, "name") for x in mem if g(x, "type") == "org"]
        for t in mteams:
            safe("is_employee_in_team", f"{u}::{t}", lambda u=u, t=t: svc.is_employee_in_team(u, t))
        for o in morgs:
            safe("is_employee_in_org", f"{u}::{o}", lambda u=u, o=o: svc.is_employee_in_org(u, o))
        safe("is_employee_in_team", f"{u}::__none__", lambda u=u: svc.is_employee_in_team(u, "__no_team__"))
        safe("is_employee_in_org", f"{u}::__none__", lambda u=u: svc.is_employee_in_org(u, "__no_org__"))
    for s in slack_ids:
        safe("is_slack_user_in_team", f"{s}::__none__", lambda s=s: svc.is_slack_user_in_team(s, "__no_team__"))
        safe("is_slack_user_in_org", f"{s}::__none__", lambda s=s: svc.is_slack_user_in_org(s, "__no_org__"))

    with open(out_path, "w") as f:
        json.dump(results, f, sort_keys=True)
    print(f"run: wrote {len(results)} cases to {out_path}")


def compare(a_path: str, b_path: str) -> int:
    a = json.load(open(a_path))
    b = json.load(open(b_path))
    a_keys, b_keys = set(a), set(b)
    only_a = a_keys - b_keys
    only_b = b_keys - a_keys
    common = a_keys & b_keys

    # group by method (prefix before first '|')
    from collections import defaultdict
    per_method = defaultdict(lambda: [0, 0])  # [match, mismatch]
    mismatches = []
    for k in common:
        method = k.split("|", 1)[0]
        if json.dumps(a[k], sort_keys=True) == json.dumps(b[k], sort_keys=True):
            per_method[method][0] += 1
        else:
            per_method[method][1] += 1
            if len(mismatches) < 15:
                mismatches.append(k)

    print(f"total common cases: {len(common)}  | only_main: {len(only_a)}  only_branch: {len(only_b)}")
    total_mismatch = sum(v[1] for v in per_method.values())
    print(f"TOTAL MISMATCHES: {total_mismatch}")
    print()
    print(f"{'method':42s} {'match':>7s} {'mismatch':>9s}")
    for m in sorted(per_method):
        mm = per_method[m]
        flag = "  <-- MISMATCH" if mm[1] else ""
        print(f"{m:42s} {mm[0]:7d} {mm[1]:9d}{flag}")
    if only_a:
        print("\nMethods/cases only in main (sample):", sorted(only_a)[:10])
    if only_b:
        print("\nMethods/cases only in branch (sample):", sorted(only_b)[:10])
    if mismatches:
        print("\nExample mismatching case keys:")
        for k in mismatches:
            print("  ", k)
    return 1 if (total_mismatch or only_a or only_b) else 0


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "run":
        run(sys.argv[2], sys.argv[3])
    elif mode == "compare":
        sys.exit(compare(sys.argv[2], sys.argv[3]))
    else:
        print("unknown mode", mode)
        sys.exit(2)
