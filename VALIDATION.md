# Implementation and verification record

This record separates authored assets from live execution. A generated guide or
successful static check does not prove an Aurora migration.

| Gate | Status |
|---|---|
| Customer site and downloadable bundle | Built; local browser layout verified; publication pending |
| Python and Terraform checks | 11 tests pass; Terraform init/validate and create-only cloud plan pass |
| Local Hydra login/consent/token flows | Real login and refresh probe pass; browser login/consent passes |
| Local snapshot migration and token continuity | Live validation pending |
| Aurora infrastructure apply | Applied: both Aurora writers and private DMS instance available |
| SCT assessment and comparison | Pending live Aurora environment |
| DMS full load + CDC | Pending live Aurora environment |
| 35 GiB full-scale run | Pending live Aurora environment |
| Customer-version compatibility | Customer release not yet supplied |

The website is a practice guide. Cloud steps remain rehearsal candidates until
their real output and evidence are recorded here. No instructor or customer has
completed the cloud phase merely because its page is available.

Observed local findings on 2026-09-07: native migrations seed a target `networks`
row, which the empty-target gate correctly rejected. This seed needs explicit
removal in the disposable target before DMS load. The first browser login hit an
upstream connection closure; a repeated browser flow and HTTP login/refresh probes
passed. A workload run issued 44 tokens but reported four connection resets during
client operations; its failure remains open and is not counted as a passing run.
The small generator run measured 22,871,962 client bytes across 2,501 client rows.

The repeated workload passed: 60 tokens, 16 revocations, four client create/update/delete cycles, zero errors. Using the explicit IPv4 admin endpoint avoids the stale Docker Desktop IPv6 listener while OrbStack owns the IPv4 mapping. The guarded target preparation removed exactly one seed network row.
