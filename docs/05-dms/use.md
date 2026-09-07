# Observe CDC behavior

1. Create a transient client through the source API. Observe its arrival in PostgreSQL.
2. Update its metadata, then delete it. Prove each change reaches the target.
3. Issue and revoke a token. Identify the database changes involved.
4. Increase the workload briefly and compare source versus target lag. Explain which side is falling behind.
5. Stop workload activity and observe pending changes drain. Explain why that alone does not justify cutover.

<details markdown="1"><summary>Monitoring hint</summary>

Compare task state, table statistics, validation results, and CloudWatch together. If the task is stopped, fresh low-lag metrics cannot be assumed. Check metric timestamps and missing-data behavior.

</details>

**Gate:** demonstrate insert, update, and delete replication, then record steady-state performance and a plan for pausing all writers.
