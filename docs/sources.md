# Sources, assumptions, and verification

## Official references

- [Hydra v2.2.0 source](https://github.com/ory/hydra/tree/v2.2.0) - demo version and database migrations.
- [Ory Hydra application example](https://www.ory.com/blog/run-oauth2-server-open-source-api-security) - login/consent integration.
- [Ory production preparation](https://www.ory.com/docs/hydra/self-hosted/production) - secrets, administrative API, and initial state.
- [AWS SCT supported conversions](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Welcome.html).
- [Install AWS SCT](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Installing.html).
- [MySQL source for SCT](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Source.MySQL.html) - JDBC, TLS, and permissions.
- [MySQL source for DMS](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.MySQL.html) - writer/binlog prerequisites.
- [PostgreSQL target for DMS](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.PostgreSQL.html) - constraints, permissions, sequences, endpoint settings.
- [DMS TLS settings](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Security.SSL.html).
- [DMS DDL handling](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TaskSettings.DDLHandling.html).
- [DMS validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html).
- [DMS monitoring](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Monitoring.html).
- [Create an RDS DB instance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CreateDBInstance.html).
- [RDS creation settings](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CreateDBInstance.Settings.html).
- [RDS PostgreSQL parameters](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.PostgreSQL.CommonDBATasks.Parameters.html).
- [RDS PostgreSQL TLS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html).
- [RDS storage](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Storage.html).
- [RDS managed credentials](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-secrets-manager.html).
- [RDS instance deletion](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_DeleteInstance.html).
- [DMS supported targets](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Introduction.Targets.html).

## Assumptions that must be checked

| Item | Current demo decision |
|---|---|
| Hydra release | v2.2.0, provisional open-source baseline |
| Source | Aurora MySQL 3.x, cluster with one writer |
| Target | RDS for PostgreSQL 17.x, Single-AZ DB instance, regional version selected explicitly |
| Target storage | 100 GiB encrypted gp3, autoscaling maximum 200 GiB; measure actual capacity needs |
| Network | One sandbox account, two VPCs, direct private peering |
| Application hosting | Docker on an SSM runner; EKS is not provisioned |
| Dataset | 35 GiB client/metadata-heavy scale profile plus real API workload |
| SCT | Assessment/conversion comparison; native Hydra schema authoritative |
| DMS | Full load + CDC, exact table selection, schema DDL disabled |
| Portal exposure | Loopback/SSM only; synthetic login, not production authentication |
| Rollback | Safe pre-write abort; post-write reverse migration is not implemented |

Read the `VALIDATION.md` included in the downloadable project for actual execution status. Authored instructions and static tests are not cloud execution evidence.

## Delivery model

The guide follows the module navigation and instructional style of the [Kayci training portal](https://hapi-suta.github.io/laas-kayci-devops-dba/). Every module includes Concepts, Build, Use, and Survive. This customer's purpose is migration practice, so interview preparation is not part of this track.
## Implementation research

Read the [dated research and decision log](research.md) for the source-to-design
mapping, pinned cloud versions, SCT CLI workflow, and evidence limits.
