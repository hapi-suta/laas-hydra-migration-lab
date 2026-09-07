# Locate the AWS services you will use

Sign in to your assigned sandbox and choose us-east-1. Use the Console search bar
to locate VPC, EC2, RDS, DMS, IAM, Secrets Manager and CloudWatch. Record the account
ID and selected role from the account menu.

Open CloudShell and run `aws sts get-caller-identity` to confirm the same identity.
This is the AWS CLI control terminal. Your private database clients will run on
the EC2 runner you create next; SCT desktop runs on your own supported workstation.

Complete [Before you begin](../start.md), then [create the AWS environment](../02-aws/console.md).
No instructor-prepared resource or script output is required.
