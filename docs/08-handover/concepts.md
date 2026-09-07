# Turn the rehearsal into a repeatable runbook

A customer lab is complete when a second person can reproduce the result from the guide and evidence. A one-off successful transfer is insufficient if the versions, data profile, task settings, and cutover decisions are unknown.

The handover package should include exact software versions, database settings, schema assessment, table mappings, dataset measurements, workload settings, DMS configuration, failure exercises, and application acceptance results. Keep raw secrets and tokens out of the published package.

Distinguish three outcomes: source application demonstrated, local migration authoring checks passed, and actual Aurora/DMS rehearsal passed at full scale. None implies the next. Record unresolved differences from the customer's production topology, including account separation, EKS, Helm, and deployment automation.

Resetting the environment is a taught operation. The target database cannot simply be reused with `DO_NOTHING` after it has accepted application writes. Start the next cohort from known snapshots or a fresh lab name and repeat schema preparation, inventory, full load, and validation.

Teardown must account for every resource you created: DMS tasks, endpoints, and imported certificates. Retained database snapshots and Secrets Manager recovery windows continue to exist after infrastructure deletion. Document those retention decisions rather than force-deleting them to obtain a clean resource list.
