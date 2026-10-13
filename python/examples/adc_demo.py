#!/usr/bin/env python3
"""Load org data from GCS using Application Default Credentials (ADC).

Authenticate first:  gcloud auth application-default login
Install deps:        pip install "orgdatacore[gcs] @ git+ssh://git@github.com/hoxhaeris/cyborg-data.git#subdirectory=python"
"""

from datetime import timedelta

from orgdatacore import GCSConfig, GCSDataSource, Service

config = GCSConfig(
    bucket="resolved-org",
    object_path="orgdata/comprehensive_index_dump.json",
    project_id="openshift-crt",
    check_interval=timedelta(minutes=5),
)

service = Service()
service.load_from_data_source(GCSDataSource(config))

version = service.get_version()
print(f"Loaded {version.employee_count} employees, {version.org_count} orgs")

emp = service.get_employee_by_uid(service.get_all_employee_uids()[0])
if emp:
    print(f"Example: {emp.full_name} ({emp.uid})")
    print(f"  Teams: {service.get_teams_for_uid(emp.uid)}")
