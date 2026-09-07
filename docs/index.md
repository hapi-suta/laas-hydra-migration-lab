# Hydra Aurora Migration Lab

**Aurora MySQL → Aurora PostgreSQL · AWS SCT · AWS DMS · Application continuity**

## Build your own migration lab from scratch

You create every lab resource yourself: networking, database clusters, the Hydra
application, restored MySQL data, SCT connections and assessment, DMS endpoints and
migration task. Then you demonstrate full load, change replication, validation,
and application cutover.

Start with your own empty lab namespace in the assigned sandbox account. Earlier
engineering tests are evidence for the guide; they are not your completed lab.
You do not need an instructor to provision resources or run migration helpers.
Choose the **Console / SCT GUI** instructions or their **native CLI** equivalents
at each stage. Complete the same verification before moving on.

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
| [01 - Understand the migration](01-demo/build.md) | Architecture, worksheet and acceptance criteria |
| [02 - Build AWS](02-aws/build.md) | Two VPCs, two Aurora clusters, a runner, and DMS |
| [03 - Restore MySQL](03-data/build.md) | Your own SQL restore, measured 35 GiB dataset and working Hydra |
| [04 - Assess with SCT](04-sct/build.md) | Assessment report and reviewed table mappings |
| [05 - Migrate with DMS](05-dms/build.md) | Full load followed by continuous replication |
| [06 - Validate and cut over](06-cutover/build.md) | Reconciled data and successful preexisting sessions |
| [07 - Survive failures](07-incidents/build.md) | Incident diagnosis and recovery evidence |
| [08 - Repeat and hand over](08-handover/build.md) | A repeatable runbook and cleanup record |

## What counts as completion?

A database connection or a green DMS task is only one checkpoint. Completion requires the requested dataset size, successful row reconciliation, proof that old refresh tokens work on the new backend, successful new logins, and a documented recovery boundary.

Begin with prerequisites, then **Module 02** to create your AWS environment.
Module 01 explains the migration before you build. Follow Modules 03-08 in order.

**Engineering validation so far:** Aurora provisioning, Hydra login/refresh and
DMS endpoint TLS tests passed. SCT generated assessment artifacts with action
items requiring review. The complete 35 GiB DMS migration and cloud cutover are
not yet verified. See [the validation record](validation.md). Record your own results; reading a page does not pass a gate.

[Begin with prerequisites](start.md) · [Download application source and reference assets](downloads/hydra-practice.zip) · [Bundle checksum](downloads/SHA256SUMS)
