# Your private lab worksheet

Copy this worksheet into your own private notes before creating resources. Fill
in each value when AWS returns it. Store secret ARNs here, never secret values.
Use one new prefix throughout the lab. If CloudShell closes, restore needed Bash
variables from these entries with `export VARIABLE=YOUR_RECORDED_VALUE`.

| Variable | What to record | Your value |
|---|---|---|
| Laptop / SCT desktop | Your Mac model/macOS version and your Windows EC2 SCT desktop | |
| AWS sign-in | Assigned portal link, account label and training role; no passwords | |
| CLI login | Approved login method; for SSO, its start URL and SSO Region | |
| LAB_ACCOUNT | STS Account ID | |
| LAB | Unique resource prefix | |
| AWS_REGION | us-east-1 | |
| AZ_A / AZ_B | Two available AZ names | |
| SOURCE_VPC / TARGET_VPC | VPC IDs and CIDRs | |
| SOURCE_A / SOURCE_B | Source database subnet IDs | |
| TARGET_A / TARGET_B | Target database subnet IDs | |
| RUNNER_SUBNET | Runner subnet ID | |
| SOURCE_RT / TARGET_RT / RUNNER_RT | Three custom route-table IDs | |
| PEER / IGW | Peering connection and internet gateway IDs | |
| SOURCE_SG / TARGET_SG | Database security-group IDs | |
| RUNNER_SG / DMS_SG / SECRETS_SG | Other security-group IDs | |
| MYSQL_VERSION / PG_VERSION | Exact selected Aurora MySQL / RDS PostgreSQL versions | |
| Source cluster | Aurora cluster identifier | |
| SOURCE_WRITER_ID / TARGET_DB_ID | Source writer / target RDS DB instance identifiers | |
| SOURCE_HOST / TARGET_HOST | Source cluster writer / target DB instance endpoints | |
| Target storage / availability | Allocated GiB, gp3, Single-AZ or Multi-AZ instance | |
| Source / target master secret | RDS-managed secret ARNs only | |
| RUNNER_ID | EC2 instance ID | |
| SCT_INSTANCE_ID / SCT_KEY_NAME | Windows EC2 instance ID and its dedicated key-pair name; no private key contents | |
| SCT root volume / Mac evidence | Windows root EBS ID, DeleteOnTermination and your Mac evidence-folder path | |
| Runner root volume | EBS volume ID and DeleteOnTermination | |
| SECRETS_VPCE | Secrets Manager interface endpoint ID | |
| DMS_VERSION / DMS_ARN | Version and replication-instance ARN | |
| SOURCE_SECRET / TARGET_SECRET | Dedicated DMS credential secret ARNs | |
| DMS_SECRET_ROLE | DMS Secrets Manager role ARN | |
| DMS_CA | Imported DMS certificate ARN | |
| SOURCE_ENDPOINT / TARGET_ENDPOINT | DMS endpoint ARNs | |
| TASK_ARN | Migration task ARN | |
| Task CloudWatch dimensions | Exact names/values from list-metrics | |
| Alarm / log group | Exact names for inspection and cleanup | |
| Fixture | Filename, SHA-256, expected counts/bytes | |
| SCT | Build, drivers, trust-store path, project/report paths | |
| Guide / application version | Git commit and Hydra v2.2.0 | |
| Budget / cleanup date | Spend limit, owner, deletion date | |
| Retained resources | Final snapshots, logs, secret recovery dates | |

## Evidence checklist

- Private source writer and target DB instance Available, DMS Available and runner SSM Online.
- Verified source/target TLS, source ROW/FULL binlogs and 72-hour retention.
- Empty-source check, successful restore exit and exact manifest comparison.
- Source application login/refresh/revocation and visible API changes.
- SCT report, 17 JSON/12 date items checked against your actual report, reviewed SQL.
- Reviewed 14-table mapping, maximum LOB check, empty native application target.
- DMS connection tests, full load, CDC insert/update/delete and row validation.
- Writer fence, CDC drain, exact counts, 28 FK checks and owned sequence review.
- Existing Alice refresh on target, new Bob login/revocation and measured downtime.
- Deleted resources and deliberate retention recorded.

Counts above describe the pinned engineering baseline. Reconcile differences in
your own schema rather than editing your evidence to match this worksheet.
