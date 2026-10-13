# CI build root image with Python and pyright for type checking
FROM registry.ci.openshift.org/openshift/release:rhel-9-release-golang-1.23-openshift-4.19

# Install Python 3.12 and development tools
RUN dnf install -y python3.12 python3.12-pip python3.12-devel && \
    dnf clean all

# Install Python CI tools
RUN python3.12 -m pip install --no-cache-dir pytest ruff pyright
