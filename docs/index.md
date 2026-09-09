# Comcast practice lab: move Hydra from Aurora MySQL to RDS PostgreSQL

You are helping Comcast's team practise a database move. In this training story,
a sign-in service uses **Aurora MySQL**. The team wants to move its data to
**RDS PostgreSQL** and check that people can still sign in.

Alice will sign in before the move. She needs to keep using her existing login
after it. Bob will start a new session after the move. Your job is to make
both work, and show the team the checks that prove it.

This is a personal AWS sandbox. You create the AWS environment, restore the
practice data, run the migration and test the application yourself. A separate
migration-only path is available later when an environment has already been
prepared for you. This is a Comcast training scenario using synthetic data, not
Comcast production data.

## Start on your Mac

On your Mac, open Safari or Chrome. Open this guide in one tab and your assigned
**AWS Console** in another.
Your laptop is where you read the guide, manage AWS and later use the app.
You create a Linux computer in AWS, called the **runner**, to run Hydra and the
database commands. For SCT, you open a temporary Windows EC2 desktop from your Mac. Aurora MySQL and RDS PostgreSQL also run in AWS.

**Your first step: [Start the full AWS build](start.md).** You will create the
network, EC2 runner, Aurora MySQL source, RDS PostgreSQL target and DMS support
resources in your personal sandbox before practising the migration.

## What you will see

| Part of the story | What you do | What you should see |
|---|---|---|
| Before the move | Sign in as Alice | **Active backend: source** and **Verified by source** |
| While data is copying | Keep using the app; create and change a test client | The app still uses MySQL; the changed row also appears in PostgreSQL |
| During the switch | Pause new activity and finish the checks | The portal is unavailable until the checks and switch finish |
| After the move | Refresh Alice's existing token; sign in as Bob | **Active backend: target** and **Verified by target** |
| Final check | Revoke Bob's token and try to use it again | Hydra rejects it and the portal asks Bob to sign in again |

Ory Hydra is the real OAuth server behind the exercise. OAuth is the sign-in and
access flow you will test. Hydra has no built-in user dashboard, so this lab
includes a small practice portal with Alice and Bob's login and consent screens.
The portal talks to Hydra; Hydra stores its data in the database.

## The project

| Component | Its job |
|---|---|
| Aurora MySQL, the **source** | The old database that the app uses first |
| RDS PostgreSQL, the **target** | The new database that the app will use after the move |
| AWS SCT, Schema Conversion Tool | Checks the table designs and produces SQL for you to review |
| AWS DMS, Database Migration Service | Copies the existing rows and then follows new changes |
| Hydra and the practice portal | Let you see whether sign-in and access still work |

- Before cutover: **Portal → Hydra → Aurora MySQL**.
- During migration: **Aurora MySQL → DMS → RDS PostgreSQL**.
- After cutover: **Portal → Hydra → RDS PostgreSQL**.

## Choose your path

The full-build path is the main customer exercise because this is a personal
sandbox. The migration-only path is useful for repeating SCT, DMS and cutover
after the environment already exists.

- [Full AWS build: create the environment yourself](start.md)
- [Migration practice: use an already-prepared environment](migration-path.md)

## Full-build tasks

Follow the **AWS Console path first**. The matching AWS CLI path comes after it
for learners who want to repeat the work using commands.

Each task explains **where to work, what to do, why you are doing it, and what
to expect**. Stop at each check. A green AWS status alone does not prove that the
application works.

- [Build the source and target](lab/01-build.md).
- [Restore data and run Hydra](lab/02-restore.md).
- [Assess the schema with SCT](lab/03-sct.md).
- [Migrate with DMS and watch live changes](lab/04-dms.md).
- [Cut over to RDS PostgreSQL](lab/05-cutover.md).
- [Prove the app works and clean up](lab/06-prove.md).

Start with [Before you begin](start.md), then task 1. Keep [your worksheet](worksheet.md)
beside you. Save your own resource IDs and results as you go.

## How to read the expected outputs

The guide shows the important fields from successful checks. Your AWS account ID,
resource IDs, endpoints, passwords, token values and timestamps will differ.
Values shown as `YOUR_...` must be replaced. Do not copy the author's AWS values.

The full restore file contains **2,236,700 clients** before the app starts. The
author's separate migration dataset contained **2,172,001 clients**. When checking
DMS, compare your own source and target counts. Starting the portal and doing
the exercises can add rows, so the two dataset counts are not interchangeable.

[What has actually been tested](validation.md) · [Download the lab files](downloads/hydra-practice.zip) · [Download checksum](downloads/SHA256SUMS)
