# Schema conversion and application compatibility

AWS SCT evaluates the source schema and proposes PostgreSQL equivalents. DMS moves data and applies changes. Hydra's own migration tool establishes the schema expected by its PostgreSQL persistence code. Those responsibilities overlap, but they are not interchangeable.

For this application, use SCT in a separate `sct_compare` database. Generate a fresh native PostgreSQL Hydra schema in `hydra`, then compare the two. Do not let SCT overwrite the application target or replace native migration bookkeeping merely because the SQL compiles.

The review must cover table names, missing tables, database-to-schema mapping, primary and foreign keys, types, nullability, defaults, collations, timestamps, binary values, and indexes. MySQL database `hydra` maps to PostgreSQL schema `public` inside database `hydra` in this lab.

Some required data may live in a table such as `networks` that does not begin with `hydra_`. The inventory helper enumerates actual tables and marks names containing `migration` as candidate bookkeeping exclusions. You must review those exclusions. The tool refuses to generate DMS mappings until you explicitly mark the inventory reviewed.

Column-name agreement does not establish type compatibility. Compare each source type with its target representation and exercise real records. Stored encrypted content must survive byte-for-byte where appropriate, while booleans and structured JSON may require comparison in canonical form.

DMS limited LOB mode is set to 64 KiB in the provided task. Before using it, scan every selected LOB column. Any larger value blocks the task setup. If the customer's real data needs full LOB mode, first rehearse its nullable-column and constraint implications instead of changing the setting blindly.

**Output:** the SCT assessment, exported conversion SQL, discrepancy worksheet, exact reviewed inventory, and explicit table mappings. None of these outputs is a claim that SCT alone makes Hydra compatible with PostgreSQL.
