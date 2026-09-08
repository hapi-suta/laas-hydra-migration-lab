# Implementation and verification record

**The AWS migration and application cutover passed.** This rehearsal used Aurora
MySQL as the source and an RDS PostgreSQL DB instance as the target. The student's
lab remains a separate build that they perform themselves.

| Check | Observed result |
|---|---|
| Full downloadable fixture | Complete native Aurora restore passed; 2,236,700 clients; all-row measurements match its manifest |
| Source volume | 2,172,001 clients, 37,590,483,214 logical bytes (35.0089 GiB) |
| LOB scan | Largest value 17,260 bytes, within the 64 KiB limit |
| RDS target | PostgreSQL 17.11; verified TLS, unencrypted connection rejection, native Hydra migrations and API CRUD passed |
| SCT | Build 677; reviewed comparison SQL applied with 15 tables, 17 JSONB columns, 12 current-time defaults and 28 foreign keys |
| DMS full load | All 14 tables completed; approximately 19.9 minutes in this rehearsal |
| DMS row validation | All 14 tables validated; zero failed, pending or suspended rows |
| CDC | Client insert, update and delete observed on both databases |
| Independent comparison | Every selected row read from both engines; canonical hashes and exact counts matched for all 14 tables |
| Relationships and sequences | 28 foreign keys checked, zero orphans; 2 owned sequences reset |
| Application cutover | Existing Alice access and refresh worked on RDS; new Bob login, refresh and revocation passed |
| Browser checks | Retained session, unchanged subject, new login and rejection of revoked refresh confirmed through the AWS portal |
| Issuer and signing keys | Unchanged across cutover |

[Download the aggregate rehearsal evidence](docs/assets/rehearsal.json). It contains
counts, timings and verification results, without passwords, cookies, tokens,
private signing keys or AWS account identifiers.

## What the timing means

The recorded interval from stopping source traffic to successful target discovery
was 33.3 minutes. It includes the
manual verification window and complete row comparison. It is not a production
outage prediction or a zero-downtime claim. The large metadata scans are I/O heavy.
The complete source-size and LOB scan took 1,049 seconds with four workers.

## What this does not claim

The migration dataset used generated SQL inserts and actual Hydra OAuth activity.
After cutover, the complete published SQL fixture was separately downloaded and
restored, unchanged, into an isolated Aurora MySQL database using the native MySQL
client. Its checksum and gzip checks passed, both import processes exited 0,
and all 2,236,700 client records were measured. The result was
37,582,389,656 logical client bytes, matching the published
manifest. All table counts matched, there were zero client/network orphans, and
Hydra v2.2.0 passed its schema check, readiness check and first/middle/last client
reads against the restored database.

Downloading and restoring the full fixture took 23.5 minutes in this
run; the complete restore and verification took 42.5 minutes.
These are two separate datasets and tests. The DMS client count of 2,172,001
and the fixture count of 2,236,700 must not be substituted for each other.

AWS Console and SCT desktop GUI steps are based on official documentation. The
executed cloud rehearsal used CLI, SQL and SCT batch operations. It does not claim
that every Console or desktop screen was personally replayed. A separate Windows
Server 2022 EC2 check verified the signed SCT 1.0.677 MSI installation, JDBC
downloads, PowerShell TCP checks to both private databases, and Mac Windows App
login through Session Manager and SCT desktop startup. The complete GUI conversion and Mac report
export have not been replayed end to end.

The dataset is deliberately dominated by repeated client metadata. It exercises
volume, JSON, LOBs, keys, types and application continuity. It is not a measured
customer data distribution. The customer Hydra version has not been supplied;
this lab pins v2.2.0 on both engines.

## Corrections found through testing

- Full load succeeded but CDC initially rejected UUID values with PostgreSQL
  error `22P02`. The final mappings explicitly transfer the 17 MySQL CHAR UUID
  columns as DMS `string(36)` into the unchanged native UUID target columns.
  A fresh insert, update and delete passed. Resume did not replay the earlier
  rejected insert, so the rehearsal reset the target data and repeated full load
  with the corrected mappings before final validation and cutover.
- Read `rds.force_ssl` through the RDS parameter group. It is not available as a
  PostgreSQL `SHOW` setting. Verify the actual connection with `pg_stat_ssl` too.
- SCT's raw export required JSON and timestamp-default repairs, removal of
  obsolete OIDS clauses, an empty-string default correction and the restored
  flow CHECK expression. The reviewed conversion applies only to sct_compare;
  the application target uses Hydra's native schema.
- A sign-out page alone did not prove token revocation. The portal now retries the
  revoked refresh token and requires rejection. This Hydra build returned HTTP
  401 `token_inactive`. Unrelated authentication failures do not count as a pass.
- OAuth checks now verify the subject, active status and client identity. A
  restarted portal checks its active backend and never seeds a missing target client.

## Guide checks

Twenty-two automated checks cover mapping selection, type normalization, identity
and revocation failures, SQL sequence handling, local links and anchors, Bash
syntax and exclusion of private files from the downloadable bundle. Desktop and
mobile browser checks cover all six tasks and their expandable instructions.
The native AWS CLI operations, option names and waiters were checked against SDK
models. This structural check does not substitute for the student's IAM access.

The student creates the networking, Aurora source, RDS target, app, restore,
SCT project and DMS task, then performs validation, cutover and cleanup. Reading
this evidence does not complete their lab.
