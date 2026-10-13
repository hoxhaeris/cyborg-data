#!/usr/bin/env python3
"""Test script: verify anonymization with real GCS data.

Loads data from the default bucket, anonymizes it, and verifies that
get_employee_by_slack_id and get_employee_by_github_id work with nonces.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

from datetime import timedelta

from orgdatacore import (
    AnonymizingDataSource,
    GCSConfig,
    GCSDataSourceWithSDK,
    PIIMode,
    Service,
)

if GCSDataSourceWithSDK is None:
    print("ERROR: google-cloud-storage not installed. Run: pip install orgdatacore[gcs]")
    sys.exit(1)


def main():
    bucket = os.environ.get("GCS_BUCKET", "resolved-org")
    object_path = os.environ.get("GCS_OBJECT_PATH", "orgdata/comprehensive_index_dump.json")
    project_id = os.environ.get("GCS_PROJECT_ID", "openshift-crt")

    print(f"Loading from gs://{bucket}/{object_path} ...")

    config = GCSConfig(
        bucket=bucket,
        object_path=object_path,
        project_id=project_id,
        check_interval=timedelta(minutes=5),
    )
    gcs_source = GCSDataSourceWithSDK(config)

    # --- Load WITHOUT anonymization (to grab some real IDs) ---
    print("\n=== Loading without anonymization ===")
    svc_full = Service()
    svc_full.load_from_data_source(gcs_source)

    version = svc_full.get_version()
    print(f"  Employees: {version.employee_count}, Orgs: {version.org_count}")

    # Find first employee with both slack_uid and github_id set
    sample_uid = None
    sample_slack = None
    sample_github = None
    for uid in svc_full.get_all_employee_uids():
        emp = svc_full.get_employee_by_uid(uid)
        if emp and emp.slack_uid and emp.github_id:
            sample_uid = uid
            sample_slack = emp.slack_uid
            sample_github = emp.github_id
            break

    if not sample_uid:
        print("  No employee found with both slack_uid and github_id set!")
        sys.exit(1)

    print(f"  Sample employee: uid={sample_uid}")
    print(f"    slack_uid:  {sample_slack}")
    print(f"    github_id:  {sample_github}")

    # Verify lookups work without anonymization
    emp_by_slack = svc_full.get_employee_by_slack_id(sample_slack)
    emp_by_github = svc_full.get_employee_by_github_id(sample_github)
    assert emp_by_slack is not None, "get_employee_by_slack_id failed (no anonymization)"
    assert emp_by_github is not None, "get_employee_by_github_id failed (no anonymization)"
    assert emp_by_slack.uid == sample_uid
    assert emp_by_github.uid == sample_uid
    print("  Slack/GitHub lookups work (no anonymization)")

    # --- Load WITH anonymization ---
    print("\n=== Loading with anonymization ===")
    anon_source = AnonymizingDataSource(gcs_source, PIIMode.ANONYMIZED)
    svc_anon = Service()
    svc_anon.load_from_data_source(anon_source)

    version_anon = svc_anon.get_version()
    print(f"  Employees: {version_anon.employee_count}, Orgs: {version_anon.org_count}")

    # Original IDs should NOT work
    assert svc_anon.get_employee_by_uid(sample_uid) is None, \
        "Original UID should not resolve in anonymized mode"
    assert svc_anon.get_employee_by_slack_id(sample_slack) is None, \
        "Original Slack ID should not resolve in anonymized mode"
    assert svc_anon.get_employee_by_github_id(sample_github) is None, \
        "Original GitHub ID should not resolve in anonymized mode"
    print("  Original IDs correctly return None")

    # Get nonces from the anonymizing source
    uid_nonce = anon_source.anonymize_uid(sample_uid)
    slack_nonce = anon_source.slack_id_to_nonce_map.get(sample_slack)
    github_nonce = anon_source.github_id_to_nonce_map.get(sample_github)

    print(f"  Nonces for sample employee:")
    print(f"    uid_nonce:    {uid_nonce}")
    print(f"    slack_nonce:  {slack_nonce}")
    print(f"    github_nonce: {github_nonce}")

    assert uid_nonce and uid_nonce.startswith("HUMAN-"), f"Bad UID nonce: {uid_nonce}"
    assert slack_nonce and slack_nonce.startswith("SLACK-"), f"Bad Slack nonce: {slack_nonce}"
    assert github_nonce and github_nonce.startswith("GITHUB-"), f"Bad GitHub nonce: {github_nonce}"

    # Nonce-based lookups should work
    emp_by_uid = svc_anon.get_employee_by_uid(uid_nonce)
    emp_by_slack = svc_anon.get_employee_by_slack_id(slack_nonce)
    emp_by_github = svc_anon.get_employee_by_github_id(github_nonce)

    assert emp_by_uid is not None, "get_employee_by_uid(nonce) returned None"
    assert emp_by_slack is not None, "get_employee_by_slack_id(slack_nonce) returned None"
    assert emp_by_github is not None, "get_employee_by_github_id(github_nonce) returned None"

    # All three lookups should return the same anonymized employee
    assert emp_by_uid.uid == uid_nonce
    assert emp_by_slack.uid == uid_nonce
    assert emp_by_github.uid == uid_nonce

    # PII should be anonymized
    assert emp_by_uid.full_name == "[ANONYMIZED]"
    assert emp_by_uid.email == "[ANONYMIZED]"
    assert emp_by_uid.slack_uid == slack_nonce
    assert emp_by_uid.github_id == github_nonce

    print("  Nonce-based lookups work:")
    print(f"    get_employee_by_uid({uid_nonce}) -> OK")
    print(f"    get_employee_by_slack_id({slack_nonce}) -> OK")
    print(f"    get_employee_by_github_id({github_nonce}) -> OK")
    print(f"    full_name = {emp_by_uid.full_name!r}")
    print(f"    email     = {emp_by_uid.email!r}")
    print(f"    slack_uid = {emp_by_uid.slack_uid!r}")
    print(f"    github_id = {emp_by_uid.github_id!r}")

    # Reverse resolution
    resolved_uid = anon_source.resolve(uid_nonce)
    assert resolved_uid == sample_uid, f"resolve() returned {resolved_uid}, expected {sample_uid}"
    print(f"\n  Reverse resolution: {uid_nonce} -> {resolved_uid}")

    print("\n=== ALL CHECKS PASSED ===")


if __name__ == "__main__":
    main()