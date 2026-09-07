# Diagnose a missing network path

Use a dedicated disposable practice environment. Before changing a security-group rule, save its exact rule ID and contents.

The instructor removes only the DMS-to-source ingress rule from the source database group. The portal can still work because the runner retains access, while the DMS endpoint connection test fails.

Compare those two observations. Check source readiness, name resolution, peering state, return routes, and the endpoint test failure. Restore only the missing lab rule, keeping the database private.

Validation requires both a successful source endpoint test and an explanation of why the working portal did not prove DMS connectivity. Run `terraform plan` afterward and resolve drift; do not leave the manually repaired rule inconsistent with managed configuration.

**Record:** rule before the incident, failed connection evidence, restored rule, successful endpoint test, and drift result. Do not inject this scenario while a timed full-load run is being measured.
