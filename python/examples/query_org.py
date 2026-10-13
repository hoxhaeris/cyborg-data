#!/usr/bin/env python3
"""Query org structure using orgdatacore with GCS."""

from datetime import timedelta

from orgdatacore import GCSConfig, GCSDataSource, Service

config = GCSConfig(
    bucket="resolved-org",
    object_path="orgdata/comprehensive_index_dump.json",
    project_id="openshift-crt",
    check_interval=timedelta(minutes=5),
)

svc = Service()
svc.load_from_data_source(GCSDataSource(config))

# Org structure — print the full hierarchy tree
def print_tree(node, indent=0):
    prefix = "  " * indent + ("└ " if indent else "")
    print(f"{prefix}{node.name} ({node.type})")
    for child in node.children:
        print_tree(child, indent + 1)

for org in svc.get_all_orgs():
    tree = svc.get_descendants_tree(org.name)
    if tree:
        print_tree(tree)
        print()
