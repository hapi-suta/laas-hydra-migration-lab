data "aws_availability_zones" "available" {
  state = "available"
}
data "aws_caller_identity" "current" {}
data "aws_ssm_parameter" "ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}
locals {
  networks = { source = "10.81.0.0/16", target = "10.82.0.0/16" }
  subnets = { for pair in setproduct(keys(local.networks), [0, 1]) : "${pair[0]}-${pair[1]}" => {
    network = pair[0], az = pair[1], cidr = cidrsubnet(local.networks[pair[0]], 8, pair[1] + 10)
  } }
}
resource "aws_vpc" "lab" {
  for_each             = local.networks
  cidr_block           = each.value
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.name}-${each.key}" }
}
resource "aws_subnet" "db" {
  for_each          = local.subnets
  vpc_id            = aws_vpc.lab[each.value.network].id
  cidr_block        = each.value.cidr
  availability_zone = data.aws_availability_zones.available.names[each.value.az]
  tags              = { Name = "${var.name}-${each.key}-private" }
}
resource "aws_vpc_peering_connection" "lab" {
  vpc_id      = aws_vpc.lab["source"].id
  peer_vpc_id = aws_vpc.lab["target"].id
  auto_accept = true
  accepter { allow_remote_vpc_dns_resolution = true }
  requester { allow_remote_vpc_dns_resolution = true }
  tags = { Name = var.name }
}
resource "aws_route_table" "private" {
  for_each = local.networks
  vpc_id   = aws_vpc.lab[each.key].id
  route {
    cidr_block                = local.networks[each.key == "source" ? "target" : "source"]
    vpc_peering_connection_id = aws_vpc_peering_connection.lab.id
  }
}
resource "aws_route_table_association" "private" {
  for_each       = local.subnets
  subnet_id      = aws_subnet.db[each.key].id
  route_table_id = aws_route_table.private[each.value.network].id
}
resource "aws_subnet" "runner" {
  vpc_id                  = aws_vpc.lab["source"].id
  cidr_block              = "10.81.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
}
resource "aws_internet_gateway" "runner" {
  vpc_id = aws_vpc.lab["source"].id
}
resource "aws_route_table" "runner" {
  vpc_id = aws_vpc.lab["source"].id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.runner.id
  }
  route {
    cidr_block                = local.networks.target
    vpc_peering_connection_id = aws_vpc_peering_connection.lab.id
  }
}
resource "aws_route_table_association" "runner" {
  subnet_id      = aws_subnet.runner.id
  route_table_id = aws_route_table.runner.id
}
resource "aws_security_group" "runner" {
  name   = "${var.name}-runner"
  vpc_id = aws_vpc.lab["source"].id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  # No inbound rules: the demo is accessed through SSM port forwarding.
}
resource "aws_security_group" "dms" {
  name   = "${var.name}-dms"
  vpc_id = aws_vpc.lab["target"].id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_security_group" "db" {
  for_each = local.networks
  name     = "${var.name}-${each.key}-db"
  vpc_id   = aws_vpc.lab[each.key].id
  ingress {
    from_port       = each.key == "source" ? 3306 : 5432
    to_port         = each.key == "source" ? 3306 : 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.runner.id, aws_security_group.dms.id]
  }
  depends_on = [aws_vpc_peering_connection.lab]
}
resource "aws_db_subnet_group" "db" {
  for_each   = local.networks
  name       = "${var.name}-${each.key}"
  subnet_ids = [for k, v in local.subnets : aws_subnet.db[k].id if v.network == each.key]
}
resource "aws_rds_cluster_parameter_group" "mysql" {
  name   = "${var.name}-mysql"
  family = "aurora-mysql8.0"
  parameter {
    name         = "binlog_format"
    value        = "ROW"
    apply_method = "pending-reboot"
  }
  parameter {
    name         = "binlog_row_image"
    value        = "FULL"
    apply_method = "pending-reboot"
  }
  parameter {
    name  = "require_secure_transport"
    value = "ON"
  }
}
resource "aws_db_parameter_group" "postgres" {
  name   = "${var.name}-postgres"
  family = "postgres17"
  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot"
  }
}
resource "aws_rds_cluster" "db" {
  for_each                        = { source = local.networks.source }
  cluster_identifier              = "${var.name}-${each.key}"
  engine                          = "aurora-mysql"
  engine_version                  = var.mysql_engine_version
  database_name                   = "hydra"
  master_username                 = "labadmin"
  manage_master_user_password     = true
  db_subnet_group_name            = aws_db_subnet_group.db[each.key].name
  vpc_security_group_ids          = [aws_security_group.db[each.key].id]
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.mysql.name
  storage_encrypted               = true
  backup_retention_period         = 3
  deletion_protection             = var.deletion_protection
  skip_final_snapshot             = false
  final_snapshot_identifier       = "${var.name}-${each.key}-final"
}
resource "aws_rds_cluster_instance" "writer" {
  for_each            = { source = local.networks.source }
  identifier          = "${var.name}-${each.key}-writer"
  cluster_identifier  = aws_rds_cluster.db[each.key].id
  instance_class      = var.db_instance_class
  engine              = aws_rds_cluster.db[each.key].engine
  engine_version      = aws_rds_cluster.db[each.key].engine_version
  publicly_accessible = false
  availability_zone   = data.aws_availability_zones.available.names[0]
}
resource "aws_rds_cluster_instance" "reader" {
  for_each            = var.add_readers ? { source = local.networks.source } : {}
  identifier          = "${var.name}-${each.key}-reader"
  cluster_identifier  = aws_rds_cluster.db[each.key].id
  instance_class      = var.db_instance_class
  engine              = aws_rds_cluster.db[each.key].engine
  engine_version      = aws_rds_cluster.db[each.key].engine_version
  publicly_accessible = false
  availability_zone   = data.aws_availability_zones.available.names[1]
}
# Fresh engineering namespaces only. Do not apply this target replacement to an
# older Aurora target state without a separate reviewed migration/retention plan.
resource "aws_db_instance" "target" {
  identifier                  = "${var.name}-target"
  engine                      = "postgres"
  engine_version              = var.postgres_engine_version
  instance_class              = var.db_instance_class
  db_name                     = "hydra"
  username                    = "labadmin"
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.db["target"].name
  vpc_security_group_ids      = [aws_security_group.db["target"].id]
  parameter_group_name        = aws_db_parameter_group.postgres.name
  allocated_storage           = 100
  max_allocated_storage       = 200
  storage_type                = "gp3"
  storage_encrypted           = true
  multi_az                    = false
  publicly_accessible         = false
  auto_minor_version_upgrade  = false
  backup_retention_period     = 3
  deletion_protection         = var.deletion_protection
  skip_final_snapshot         = false
  final_snapshot_identifier   = "${var.name}-target-final"
  delete_automated_backups    = false
}
resource "aws_iam_role" "dms_service" {
  for_each           = var.create_dms_service_roles ? toset(["dms-vpc-role", "dms-cloudwatch-logs-role"]) : toset([])
  name               = each.key
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "dms.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "dms_service" {
  for_each   = aws_iam_role.dms_service
  role       = each.value.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/${each.key == "dms-vpc-role" ? "AmazonDMSVPCManagementRole" : "AmazonDMSCloudWatchLogsRole"}"
}
resource "aws_dms_replication_subnet_group" "lab" {
  replication_subnet_group_id          = var.name
  replication_subnet_group_description = "Private DMS practice subnets"
  subnet_ids                           = [aws_subnet.db["target-0"].id, aws_subnet.db["target-1"].id]
}
resource "aws_dms_replication_instance" "lab" {
  replication_instance_id     = var.name
  replication_instance_class  = "dms.t3.medium"
  allocated_storage           = 100
  engine_version              = var.dms_engine_version
  auto_minor_version_upgrade  = false
  publicly_accessible         = false
  multi_az                    = false
  replication_subnet_group_id = aws_dms_replication_subnet_group.lab.id
  vpc_security_group_ids      = [aws_security_group.dms.id]
  depends_on                  = [aws_iam_role_policy_attachment.dms_service]
}
resource "aws_security_group" "endpoint" {
  name   = "${var.name}-secrets-endpoint"
  vpc_id = aws_vpc.lab["target"].id
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.dms.id]
  }
}
resource "aws_vpc_endpoint" "secrets" {
  vpc_id              = aws_vpc.lab["target"].id
  service_name        = "com.amazonaws.${var.region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.db["target-0"].id, aws_subnet.db["target-1"].id]
  security_group_ids  = [aws_security_group.endpoint.id]
  private_dns_enabled = true
}
resource "aws_secretsmanager_secret" "dms" {
  for_each                = local.networks
  name                    = "${var.name}/dms-${each.key}"
  recovery_window_in_days = 7
}
resource "aws_iam_role" "dms_secrets" {
  name               = "${var.name}-dms-secrets"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "dms.${var.region}.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy" "dms_secrets" {
  role   = aws_iam_role.dms_secrets.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"], Resource = [for s in aws_secretsmanager_secret.dms : s.arn] }] })
}
resource "aws_iam_role" "runner" {
  name               = "${var.name}-runner"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "runner_ssm" {
  role       = aws_iam_role.runner.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_role_policy" "runner_secrets" {
  role = aws_iam_role.runner.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = concat([for c in aws_rds_cluster.db : c.master_user_secret[0].secret_arn], [aws_db_instance.target.master_user_secret[0].secret_arn]) },
    { Effect = "Allow", Action = ["secretsmanager:PutSecretValue"], Resource = [for s in aws_secretsmanager_secret.dms : s.arn] }
  ] })
}
resource "aws_iam_instance_profile" "runner" {
  name = "${var.name}-runner"
  role = aws_iam_role.runner.name
}
resource "aws_instance" "runner" {
  ami                    = data.aws_ssm_parameter.ami.value
  instance_type          = "t3.large"
  subnet_id              = aws_subnet.runner.id
  vpc_security_group_ids = [aws_security_group.runner.id]
  iam_instance_profile   = aws_iam_instance_profile.runner.name
  metadata_options { http_tokens = "required" }
  root_block_device {
    volume_size = 60
    volume_type = "gp3"
    encrypted   = true
  }
  user_data = file("${path.module}/runner.sh")
  tags      = { Name = "${var.name}-runner" }
}
