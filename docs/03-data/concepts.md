# Understand what you are restoring

You create an empty Aurora MySQL database, then import a supplied logical SQL
fixture. It contains Hydra v2.2.0 table definitions, its source migration history,
one network and synthetic OAuth clients. You create real authorization, consent,
refresh and revocation state by using the application after the import.

The full fixture expands to at least 35 GiB of logical client content. Repeated
metadata compresses heavily. This tests restoration, schema differences, LOB
handling and migration checks; it does not model a customer's production data
distribution or establish production performance.

SCT assesses schema compatibility. DMS moves selected application data. MySQL
migration bookkeeping must not replace PostgreSQL's native migration history.
The real target is initialized using the same pinned Hydra version's PostgreSQL
migrations; SCT's converted output is examined in a separate comparison database.

**Explain before building:** how a compressed SQL download differs from a database
snapshot, why the destination must be empty, and why importing client metadata
alone does not prove token/session continuity.
