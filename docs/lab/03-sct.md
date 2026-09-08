# 3. Assess the schema with SCT

**Result:** an SCT assessment, reviewed conversion SQL and an empty application target ready for DMS.

SCT converts database structures. DMS copies the rows. They do different jobs.

Hydra also owns its database structure through versioned migrations. For this lab, you apply and inspect SCT's conversion in a separate database called **sct_compare**. The application uses Hydra's native PostgreSQL schema in **hydra.public**. This lets you practice SCT and compare its decisions against the schema Hydra expects.

## What Comcast is checking

A table defines the fields in each record and the types of values they accept. MySQL and PostgreSQL do not use all the same types or defaults. You will ask SCT to assess those differences, inspect the SQL it produces, and fix the reported issues.

The portal still uses MySQL throughout this task. Open Alice's **Protected account** before and after your SCT work. Both times it should show **Verified by source**. Creating a target table does not switch the application.

## Run SCT

Start with the SCT desktop instructions below. SCT is a separate application you install; it is not a page inside the AWS Console. The SCT command-line option follows. Use the same source database and the same comparison target in either route.

<details class="instructions" markdown="1" open>
<summary>SCT desktop: install, connect, assess and export the conversion</summary>

{{lesson:../04-sct/console.md}}

</details>

<details class="instructions" markdown="1">
<summary>SCT CLI alternative: install, connect, assess and export the conversion</summary>

{{lesson:../04-sct/build.md}}

</details>

## Review the conversion and prepare DMS

In PostgreSQL, `hydra.public` means the database named `hydra` and the schema named `public` inside it. Think of `public` as a named group of tables. `sct_compare` is a separate database for inspecting SCT's output.

DMS calls large text, JSON and binary values **LOBs**, short for large objects. You measure their size before choosing a limit. Otherwise a copy can cut a value short or fail.

The tested SCT export needed repairs to JSON types, timestamp defaults, obsolete table options, an escaped text default and a CHECK constraint. Follow the SQL review below before applying the conversion. Do not accept a successful export as proof the SQL will run.

<details class="instructions" markdown="1">
<summary>Inspect the schemas, repair the SQL, measure LOBs and verify the empty target</summary>

{{lesson:../04-sct/schema-checks.md}}

</details>

## Check before continuing

- You saved your assessment and explained every action item.
- The reviewed conversion applies to sct_compare without errors.
- Your 14-table DMS selection includes networks and excludes schema_migration.
- Every source LOB fits the selected DMS size limit.
- The 14 application target tables are empty, target migration history is retained, and target Hydra is stopped.

[Previous: 2. Restore data and run Hydra](02-restore.md) · [Next: 4. Migrate with DMS](04-dms.md)
