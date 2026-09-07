# Schema conversion and application compatibility

AWS SCT evaluates the source schema and proposes PostgreSQL equivalents. DMS moves data and applies changes. Hydra's own migration tool establishes the schema expected by its PostgreSQL persistence code. Those responsibilities overlap, but they are not interchangeable.

For this application, use SCT in a separate `sct_compare` database. Generate a fresh native PostgreSQL Hydra schema in `hydra`, then compare the two. Do not let SCT overwrite the application target or replace native migration bookkeeping merely because the SQL compiles.

The review must cover table names, missing tables, database-to-schema mapping, primary and foreign keys, types, nullability, defaults, collations, timestamps, binary values, and indexes. MySQL database `hydra` maps to PostgreSQL schema `public` inside database `hydra` in this lab.

The `networks` table does not begin with `hydra_`, but its rows are required by
foreign keys. Use the native catalog queries and the exact 14-table selection in
this guide. Review migration-bookkeeping exclusions against the actual pinned
schema. Preserve PostgreSQL's own migration history.

**Gate:** explain why the SCT comparison database and the native application target
are separate, and why every required relationship table belongs in the DMS selection.
