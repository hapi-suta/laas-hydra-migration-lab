# Restore the source through Console access

**You restore the data yourself.** Finish [Console infrastructure setup](../02-aws/console.md)
and [application setup](../02-aws/application.md) first. The Aurora MySQL cluster, RDS PostgreSQL instance,
SQL users and target schema must be your own work. The source database is empty.

## 1. Check your restore destination

1. Open **RDS → Databases → your source cluster**.
2. Confirm engine **Aurora MySQL**, status **Available** and your lab prefix.
3. Under **Connectivity & security**, copy the cluster writer endpoint, port 3306,
   source VPC and source DB security group into your worksheet.
4. Open the writer instance. Confirm **Publicly accessible: No**.
5. Check the parameter group has ROW binlogs and FULL row images. The SQL checks
   in the next step prove these values are active.

## 2. Open your runner and perform the logical restore

1. Open **EC2 → Instances → your runner → Connect → Session Manager → Connect**.
2. Run `sudo su - ec2-user`, then `cd /opt/hydra-practice`.
3. Follow [Restore MySQL, steps 1-4](build.md). Download the fixture yourself,
   check its checksum, create your private client file, prove the database is
   empty, run the import, then verify counts and bytes.
4. Keep the tmux session running while monitoring **RDS → source writer → Monitoring**.
5. Save your restore exit status and SQL results before starting Hydra.

The RDS Console does not upload a logical `.sql.gz` file into Aurora MySQL.
**Restore from S3** is a different physical-backup workflow and does not accept
this fixture. Session Manager provides the terminal for the native MySQL import;
it is the same restore operation used by the CLI route.
[AWS logical import documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Migrating.ExtMySQL.mysqldump.html).

## 3. Start and use your application

Follow [Restore MySQL, steps 5-6](build.md): run the pinned migration check, start
source/portal/gateway, verify readiness, and open the SSM portal tunnel from your
workstation. Perform the Alice and Bob browser exercises yourself.

**Checkpoint:** a screenshot of your source cluster settings, checksum result,
restore exit 0, exact SQL counts/bytes, and successful browser login/refresh.
Do not capture passwords or tokens. Proceed to the [SCT GUI lesson](../04-sct/console.md).
