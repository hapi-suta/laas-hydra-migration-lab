# Understand the AWS practice topology

The cloud stack uses two VPCs in a single sandbox account. Aurora MySQL lives in the source VPC. Aurora PostgreSQL and a private DMS replication instance live in the target VPC. Peering and return routes let DMS connect to the source writer using its native hostname.

Each cluster's subnet group spans two Availability Zones. One writer per cluster is the default for practice. Adding a reader is an explicit option for writer-failover exercises; a multi-AZ subnet group alone does not create an extra database instance.

The source VPC also contains an EC2 lab runner. Its public subnet provides outbound package downloads, but its security group accepts no inbound connections. You access its terminal and forward the practice portal using AWS Systems Manager Session Manager.

Security groups limit database ingress to the runner and DMS groups. Native Aurora endpoints preserve TLS hostname verification. An NLB or a Route 53 alias is unnecessary for this direct peering topology.

Secrets Manager holds AWS-managed administrator credentials. You retrieve those credentials privately and execute the documented SQL to create separate Hydra, SCT and DMS users. DMS uses its own Secrets Manager role and reaches the service through a target-VPC interface endpoint.

The resources incur ongoing charges while running. Budgets alert; they do not automatically shut down this stack. Track the owner, expected duration, deletion protection, final snapshots, and cleanup procedure from day one.

The EC2/Docker setup is deliberately a demo implementation. Production cross-account IAM and EKS/ArgoCD deployment mechanics are a subsequent exercise, not features silently implied by this topology.
