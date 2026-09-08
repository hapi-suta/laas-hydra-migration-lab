# 4. Migrate with DMS

**Result:** the restored rows arrive in PostgreSQL, then new MySQL changes follow automatically.

A DMS task first performs the **full load**, copying existing rows. It then uses **change data capture (CDC)** to copy inserts, updates and deletes while Hydra continues using MySQL.

## Watch the copy without moving the app

Open Alice's **Protected account** and confirm **Verified by source**. Keep the portal tab open beside the DMS Console. During full load, refresh the task's **Table statistics** to see the copied row count rise. Refresh Alice's page too: it should continue to use the source.

Even when full load reaches 100%, the portal still uses MySQL. You change that in task 5, after checking the data.

## Create and start the migration

Follow the AWS Console route first. The CLI route afterward is an alternative; do not create a second task. You create the replication users, secrets, endpoint connections, exact table selection and task settings yourself. Test both endpoints before starting the task. The mapping includes the UUID conversion rules verified during the rehearsal. Select **Full load and CDC** and **Do nothing** for target preparation because the target schema already exists.

<details class="instructions" markdown="1" open>
<summary>AWS Console: configure endpoints, create the task and monitor full load</summary>

{{lesson:../05-dms/console.md}}

</details>

<details class="instructions" markdown="1">
<summary>CLI alternative with SQL: configure endpoints, create the task and monitor full load</summary>

{{lesson:../05-dms/build.md}}

</details>

## Watch a change cross the databases

After full load completes, create one client through Hydra, update its metadata and delete it. Query both databases after each operation. This makes CDC visible instead of relying only on a green task status.

<details class="instructions" markdown="1">
<summary>Perform the insert, update and delete exercise, then inspect DMS</summary>

{{lesson:../05-dms/use.md}}

</details>

## Expected results

| Check | Expected result |
|---|---|
| Each endpoint connection test | **Successful** for both source and target. |
| Full load | All 14 selected tables complete, with no load errors. |
| Create the CDC test client | The same client ID and revision `1` appear in both databases. |
| Update the test client | Revision `2` and the changed consent setting appear in both databases. |
| Delete the test client | Both queries return no matching client. |
| Open Alice's account | **Verified by source**. |

MySQL commonly prints a boolean as `0` or `1`; PostgreSQL's psql prints `f` or `t`. These mean false and true. Compare the meaning as well as the displayed value.

Replication is not instant. Wait and query the target again after each change. If a change does not arrive, inspect the task and logs before proceeding. Do not fix a missing row by inserting it manually into PostgreSQL.

## Check before continuing

- All 14 selected tables completed full load without table errors.
- Your client insert, update and delete appeared on both databases.
- DMS remains running in CDC mode. Inspect validation and investigate failures.
- Source Hydra still serves the portal; target Hydra remains stopped.

Record the load duration and replication lag. Next you will stop source writes and check the final data before switching the app.

[Previous: 3. Assess the schema with SCT](03-sct.md) · [Next: 5. Cut over to PostgreSQL](05-cutover.md)
