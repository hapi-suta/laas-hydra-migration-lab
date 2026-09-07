# Separate data volume from application realism

This lab has two complementary data paths. `scale.py` clones a genuine API-created Hydra client record, changes its identifier and metadata, and inserts it into the existing Hydra schema. `workload.py` drives real token issuance, revocation, and client insert/update/delete requests through Hydra APIs.

The bulk profile is explicitly **client/metadata-heavy**. It is useful for full-load volume, LOB configuration, indexes, and reconciliation, but it is not presented as the customer's production token/session distribution. Production fidelity requires measured table sizes, row widths, activity rates, and tenant relationships from the customer's source.

The bulk generator keeps the template client's serialized fields, hashed secret, and network relationship. It does not modify Hydra's schema or invent usable token ciphertext. Data includes varied metadata lengths, Unicode, and multiple synthetic cohorts. A cohort is metadata, not an independent Hydra tenant.

Size is measured as the sum of stored column-value byte lengths in the client table. Indexes, allocated pages, binlogs, and Aurora replicated storage are excluded. This makes 35 GiB an actual dataset target rather than a disk-allocation claim. Source and PostgreSQL physical storage sizes need not match.

The generator first scans existing data, resumes after the highest generated client ID, inserts in bounded batches, and performs a final exact byte measurement. It is single-writer: do not run two scale processes against the same source. API workload is allowed alongside it after the initial schema is stable.

The default is a small development profile. `--full-scale` is required above 1 GiB because generation, database storage, and migration consume real resources. Run the full 35 GiB profile in AWS after the small application path works.

Avoid running Hydra's janitor during a measured rehearsal unless cleanup itself is the scenario. Token expiration remains real: mint the continuity test session shortly before cutover and record its TTL.
