# What has been tested

This record separates executed tests from documented procedures. It does not
award the student's checkpoints. Updated 2026-09-07.

| Area | Evidence | Limit |
|---|---|---|
| Aurora infrastructure | Both private writers, peered VPCs, SSM runner and private DMS instance reached Available/Online in the engineering account | The new Console and native CLI creation sequence has not been replayed from an empty AWS namespace |
| Cloud application | Hydra on Aurora MySQL passed login and refresh; a bounded API workload passed | Not a completed cloud cutover |
| SCT | Batch build 677 connected to both engines and exported assessment/conversion artifacts | JSON/default action items require review; the desktop GUI and reviewed comparison apply have not been replayed end to end |
| DMS connectivity | Both native endpoints passed verified TLS connection tests | No cloud full-load/CDC task completed |
| Small restore fixture | Restored to an isolated local MySQL 8.0.41 database; 15 table counts, 3,200 clients, 53,749,850 logical client bytes and zero client/network orphans verified | Local SQL import, not a 35 GiB Aurora restore |
| Local migration continuity | Earlier local migration matched all 14 table counts/hashes; 28 FK checks passed; retained refresh and new login passed | Local transfer used an engineering utility, not AWS DMS |
| Full fixture content | Audited all 2,236,700 SQL rows and 37,582,389,656 logical bytes; restored the final 1,000 boundary rows with zero orphans; maximum metadata value 16,880 bytes | Full-volume local imports were stopped; a complete serial 35 GiB Aurora restore, DMS validation and cloud cutover remain unverified |

## Guide and application checks

- 17 automated checks pass, including all local links/anchors, Bash syntax,
  exact table selections and exclusion of private files from the download bundle.
- Native AWS CLI operation/option names and waiters were checked against the SDK
  models, with AWS CLI-specific EC2 shorthand handled separately. This checks
  command structure, not IAM permissions or successful resource creation.
- The published SQL queries were replayed locally: 14 source/target count queries,
  semantic metadata totals, 28 generated foreign-key checks, two sequence reset
  statement plans, and the one-scan-per-table LOB query. The largest small-fixture
  value measured 16,877 bytes.
- The restored small source passed Hydra migration startup, Alice login/refresh,
  Bob login/revocation and explicit client POST/PUT/DELETE with source SQL checks.
- Browser checks passed for desktop/mobile layout, navigation, progress storage,
  and copying a complete SCT command including its slash terminator.

The guide uses AWS documentation for AWS operations and Ory documentation/source
for Hydra. Expected results explain what the student must obtain. They are not
fabricated console output or a claim that every interface was personally replayed.

The full-volume local import was stopped after slow throughput. Its partial rows
were discarded. The substitute content audit checked every SQL row, unique ID,
UUID/digest, metadata structure, byte total and commit batch, followed by a native
MySQL restore of the high-ordinal boundary rows. That is not a completed full-volume
restore. Temporary local database tuning was confined to author tests and restored
afterward; no student AWS resources were changed during this guide rewrite.

The release manifest records fixture checks separately. Synthetic repeated padding
compresses heavily and does not represent a production storage distribution.
The customer Hydra release has not been supplied; this lab pins v2.2.0 on both engines.

No student resources are provisioned by the published guide. The student creates
both Aurora systems, restores MySQL, configures SCT/DMS and performs the migration.
