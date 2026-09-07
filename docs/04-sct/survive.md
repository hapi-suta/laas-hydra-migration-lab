# Catch a missing table or unsupported conversion

Make a copy of your proposed table-mapping JSON in a local editor. Remove the
`networks` selection from that copy, without applying it to DMS. Compare the
remaining selection with the source inventory and target foreign keys. Identify
which relationships would break even if all selected rows copied successfully.

Restore the missing selection. Recheck the [14-table inventory and LOB scan](schema-checks.md)
before creating the real task. Review SCT's JSON and timestamp action items using
actual native target definitions. Keep unresolved errors visible in your worksheet.

**Gate:** detect the incomplete selection before execution and explain why a high
conversion percentage or matching subset counts cannot prove application integrity.
