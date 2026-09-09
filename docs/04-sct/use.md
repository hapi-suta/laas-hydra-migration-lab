# Explain the schema decisions

- Find one data type represented differently in MySQL and PostgreSQL. Demonstrate a round-trip comparison using a real synthetic row.
- Explain why `schema_migration` should retain target-native history while network data must follow the source.
- Find the largest LOB in the source. Explain what would happen if it exceeded the configured DMS limit.
- Compare indexes produced by SCT with those produced by Hydra. Which differences affect application lookup behavior?
- Explain why `hydra_*` selection can miss a required relationship.

<details markdown="1"><summary>Review hint</summary>

Use the exact inventory and SCT action items as your reference. Passing the mappings helper means the selected names and keys passed its structural checks; it does not replace manual type review or application tests.

</details>

**Gate:** another engineer should be able to understand every exclusion and mapping from your worksheet alone.
