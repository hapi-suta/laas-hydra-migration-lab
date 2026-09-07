# Before you begin

## Workspaces and identities

| Name in the lessons | What it means |
|---|---|
| **Laptop / your user** | Your workstation, AWS CLI, Terraform, SCT, browser |
| **Runner / ec2-user** | The disposable Amazon Linux EC2 machine in the source VPC |
| **Source** | Hydra backed by Aurora MySQL |
| **Target** | Hydra backed by Aurora PostgreSQL; kept stopped until migration completes |

Use the project root as the current directory unless a step says otherwise. On the runner it is `/opt/hydra-practice`. Do not SSH into an Aurora database: Aurora is managed; SQL connections originate from the runner or an SSM tunnel.

## Required software

Install Python 3.9 or later, Docker with Compose v2, Git, AWS CLI v2, Terraform 1.5 or later, and the AWS Session Manager plugin. Install AWS SCT and its MySQL/PostgreSQL JDBC drivers on your laptop using the official instructions linked in Sources.

For AWS work, use an instructor-approved **sandbox account** with sufficient permission for VPC, RDS, DMS, EC2, IAM, SSM, Secrets Manager, and CloudWatch. Do not use customer production credentials. Set a spending budget and teardown date before provisioning; the stack includes two paid Aurora writers, EC2, DMS, storage, and interface endpoints.

On **Laptop**, as **your user**, after extracting the downloaded bundle:

```bash
cd hydra-practice
```

On **Laptop**, as **your user**:

```bash
python3 -m venv .venv
```

`-m venv` creates an isolated Python environment in `.venv`.

On **Laptop**, as **your user**:

```bash
.venv/bin/pip install -r requirements.txt
```

`-r` reads the pinned package list. Verify the command finishes successfully; retain the installation output in your private exercise notes.

## Lab assumptions

The demo uses open-source Hydra **v2.2.0** as a provisional baseline. Confirm your customer's version before extending the findings to their deployment. Source and target use the same Hydra version. Changing engine and Hydra version simultaneously obscures the cause of failures.

The runnable cloud lab uses **one account, two VPCs, and Docker on EC2**. It practices real Aurora/DMS and private peering without first requiring EKS. Cross-account permissions, Helm/ArgoCD, and EKS cutover must be rehearsed separately before calling this a full production-topology reproduction.

All identities and secrets are generated for the lab. Runtime credentials live in ignored files with restrictive permissions. Never paste `.env`, token responses, or raw customer data into GitHub Pages.

## Save evidence

Create an `evidence` directory in the project root. Scripts produce JSON reports there. Record observations and timestamps alongside them. A lesson's browser checkbox only tracks your reading; it does not verify AWS state.

[Continue to Concepts](01-demo/concepts.md)
