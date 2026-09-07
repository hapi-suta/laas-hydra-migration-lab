# Catch a missing table before migration

The instructor provides a copy of the inventory with one required relationship table removed. Do not alter the actual source schema.

Compare the proposed selection with source foreign keys and the original inventory. Identify what application behavior could fail even if all selected tables loaded successfully.

Restore the missing table to the selection, regenerate mappings, and rerun the empty-target/LOB checks as appropriate. Explain why row counts for a selected subset can look perfect while the application is broken.

**Success:** all required parent/child relationships are accounted for and the reviewer can trace the selected tables back to the actual source inventory.
