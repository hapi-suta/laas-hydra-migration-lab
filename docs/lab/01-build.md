# 1. Build the source and target

**Result:** an Aurora MySQL source, an RDS PostgreSQL target, and a runner that can connect to both.

The runner is the EC2 machine where you install Hydra and run database commands. DMS uses a separate replication instance to copy the data. You create these resources in your own lab namespace.

Complete [Before you begin](../start.md) first. Keep [your worksheet](../worksheet.md) open to record each resource ID. This is one AWS account with two connected VPCs. Production cross-account networking and EKS are outside this practice lab.

## What Comcast needs at this point

The team needs two empty databases before it can practise moving data. Aurora MySQL will hold the current Hydra data. RDS PostgreSQL will receive the copy. The runner is a small Linux computer for the app and database tools.

There is no working portal yet. That is expected: you install it and restore its data in task 2.

## Build it

Start with the AWS Console instructions below and follow their numbered steps. The CLI option afterward creates the same resources. Use one route, so you do not create duplicate resources.

<details class="instructions" markdown="1" open>
<summary>AWS Console: create the networks, databases, runner and DMS instance</summary>

{{lesson:../02-aws/console.md}}

</details>

<details class="instructions" markdown="1">
<summary>CLI alternative: create the same resources from CloudShell</summary>

{{lesson:../02-aws/build.md}}

</details>

## Check before continuing

- Aurora MySQL has an available writer instance.
- The target is an available **RDS PostgreSQL DB instance**.
- Both databases are private, and their subnet groups span two Availability Zones.
- The runner appears in Systems Manager and opens a Session Manager shell.
- The DMS replication instance is available.

Save the source writer endpoint, target instance endpoint, security group IDs and runner ID. You will use them in the next task.

[Next: 2. Restore data and run Hydra](02-restore.md)
