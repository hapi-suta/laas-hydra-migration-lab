# AWS demo foundation

Follow [Build AWS](../docs/02-aws/build.md) for customer instructions.

This optional author reference now defines a source Aurora cluster and a target
RDS PostgreSQL DB instance. It is for a fresh engineering namespace. Do not apply
it to an earlier Aurora-target state: that would propose replacement/deletion of
the old target. This correction has not been applied to any AWS account.
The student builds each resource with the guide, not Terraform.

This is a one-account, two-VPC practice stack. It provisions actual Aurora MySQL,
RDS for PostgreSQL, private DMS, and a Docker/SSM runner. It does not provision EKS
or cross-account IAM. Account pinning is mandatory. Engine versions are explicit
inputs selected from the live regional AWS preflight.

The runner has outbound internet access but no inbound rules. Database endpoints
are private and use TLS. Secrets are generated at runtime or managed by RDS;
Terraform creates secret containers but never stores their password values.

DMS endpoints/tasks are created separately in Module 05 so the customer learns
their settings. They are not Terraform-managed and must be deleted before
Terraform destroy. DMS service roles have global account names: set
`create_dms_service_roles=false` if both already exist. Never delete shared roles.

Deletion protection defaults on. Teardown retains final database snapshots and
uses a seven-day recovery window for endpoint secrets. Reusing a lab name after
teardown may conflict with retained snapshots or pending-deletion secrets; use a
new name for a fresh cohort. Do not force-delete retained evidence to avoid that.

Before delivery, live-test engine availability, instance-class availability,
Source and target parameter support, the DMS IAM policies and PostgreSQL parameter grant,
source retention, TLS, and table validation. `terraform validate` only checks
configuration against the provider schema.
