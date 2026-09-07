# Diagnose a missing network path

Use a dedicated disposable practice environment. Before changing a security-group rule, save its exact rule ID and contents.

The instructor removes only the DMS-to-source ingress rule from the source database group. The portal can still work because the runner retains access, while the DMS endpoint connection test fails.

Compare those two observations. Check source readiness, name resolution, peering state, return routes, and the endpoint test failure. Restore only the missing lab rule, keeping the database private.

Validation requires both a successful source endpoint test and an explanation of why the working portal did not prove DMS connectivity. Run `terraform plan` afterward and resolve drift; do not leave the manually repaired rule inconsistent with managed configuration.

**Record:** rule before the incident, failed connection evidence, restored rule, successful endpoint test, and drift result. Do not inject this scenario while a timed full-load run is being measured.

## Hydra migration fails with MySQL error 1832

On the tested Aurora MySQL version, Hydra 2.2.0's native migration failed while
changing `nid`, which participates in a foreign key. The cloud Compose file sets
`foreign_key_checks=0` only on the **migrate-source** connection. It preserves
TLS verification and leaves foreign-key checks enabled for the running source
application. Do not change the cluster-wide setting or remove constraints.

On **Runner**, as **ec2-user**, after confirming that only the disposable initial
schema is being initialized:

```bash
.venv/bin/python scripts/lab.py up
.venv/bin/python scripts/oauth_probe.py login
.venv/bin/python scripts/oauth_probe.py refresh
.venv/bin/python scripts/inventory.py
```

For the Console path, open **Systems Manager → Session Manager → Start session**,
select the tagged runner, and run the same commands from its project directory
as `ec2-user`. Expect both probes to report `pass: true` and `backend: source`.
Review the schema and foreign keys before loading the large dataset. The issue
and session-scoped workaround are documented in the
[Ory issue](https://github.com/ory/hydra/issues/3363).

If TLS reports permission denied for the public CA bundle, ensure
`runtime/certs` is mode 755 and its PEM files are mode 644. The containers run
under a different UID. Keep `.env` and database credential files mode 600.
