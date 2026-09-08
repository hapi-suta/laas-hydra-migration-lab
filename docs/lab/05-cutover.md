# 5. Cut over to PostgreSQL

**Result:** Hydra serves the same portal using the migrated RDS PostgreSQL data.

Keep Alice signed in. Stop all source writers, let DMS finish applying changes, and compare the databases while the data is stable. Then stop DMS, check relationships and sequences, and start target Hydra.

Keep the same Hydra version, issuer, system secret and cookie secret. Keep the portal process running because this demo stores its browser sessions in memory.

## What Alice will experience

| Point in the switch | Expected result in the browser | Why |
|---|---|---|
| Before you pause the app | **Verified by source** | Hydra still uses MySQL. |
| After you stop the gateway | The portal does not load. | You paused access while checking the final copy. |
| After you start target Hydra and the gateway | **Verified by target** in Alice's existing session | Hydra now reads the migrated PostgreSQL records. |
| After Alice refreshes her token | Alice stays signed in on target. | The copied refresh record and original secrets still work. |

Do not close Alice's session or log in again to make this test pass. Its purpose is to test the session that existed before the switch.

## Perform the cutover in order

Follow the AWS Console route below. It includes the required runner commands and SQL checks at the point where you need them. The CLI route afterward is an alternative for the same cutover. Complete one route once.

<details class="instructions" markdown="1" open>
<summary>AWS Console: pause the app, check the data, stop DMS and switch Hydra</summary>

{{lesson:../06-cutover/console.md}}

</details>

<details class="instructions" markdown="1">
<summary>CLI alternative: perform the same cutover with AWS CLI, SQL and Docker</summary>

{{lesson:../06-cutover/build.md}}

</details>

## Check before continuing

- Source writers are stopped and DMS has finished applying the last source changes.
- Row counts match, DMS validation is complete, linked records have no missing parents, and automatic ID values are ready for new writes.
- Target Hydra is healthy and the portal opens through the target route.
- Source Hydra and the DMS task remain stopped.

Starting target Hydra can write data. From that point, MySQL can be stale. Do not switch traffic back to it after target writes without a separate recovery plan.

[Previous: 4. Migrate with DMS](04-dms.md) · [Next: 6. Prove it works and clean up](06-prove.md)
