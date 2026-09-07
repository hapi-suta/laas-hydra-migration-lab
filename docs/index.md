# Hydra Aurora Migration Lab

**Aurora MySQL → Aurora PostgreSQL · AWS SCT · AWS DMS · Application continuity**

## Welcome to your practice environment

Build a working Hydra application, populate it with synthetic data, move it to a different database engine, and prove that authentication still works. You will operate every stage yourself and keep an evidence record of what happened.

This project uses **CBUS**:

| Phase | What you do |
|---|---|
| **Concepts** | Understand the architecture and predict the result |
| **Build** | Set up each component with guided steps |
| **Use** | Practice and verify normal behavior |
| **Survive** | Diagnose a failure, recover, and explain the cause |

## Your learning journey

| Module | What you will deliver |
|---|---|
| [01 — Run the demo](01-demo/build.md) | A portal with working login, consent, and refresh |
| [02 — Build AWS](02-aws/build.md) | Two VPCs, two Aurora clusters, a runner, and DMS |
| [03 — Create data](03-data/build.md) | A measured 35 GiB profile plus live API traffic |
| [04 — Assess with SCT](04-sct/build.md) | Assessment report and reviewed table mappings |
| [05 — Migrate with DMS](05-dms/build.md) | Full load followed by continuous replication |
| [06 — Validate and cut over](06-cutover/build.md) | Reconciled data and successful preexisting sessions |
| [07 — Survive failures](07-incidents/build.md) | Incident diagnosis and recovery evidence |
| [08 — Repeat and hand over](08-handover/build.md) | A repeatable runbook and cleanup record |

## What counts as completion?

A database connection or a green DMS task is only one checkpoint. Completion requires the requested dataset size, successful row reconciliation, proof that old refresh tokens work on the new backend, successful new logins, and a documented recovery boundary.

The first module is an optional local introduction. Modules 02–08 use **real Aurora and DMS**. Cloud procedures are authored for live rehearsal and must be validated in your sandbox; check the instructor's verification record before using them as a production runbook.

[Begin with prerequisites](start.md) · [Download the runnable project](downloads/hydra-practice.zip) · [Bundle checksum](downloads/SHA256SUMS)
