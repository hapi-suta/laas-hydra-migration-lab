output "lab" {
  value = {
    account_id           = data.aws_caller_identity.current.account_id
    region               = var.region
    name                 = var.name
    runner_id            = aws_instance.runner.id
    dms_instance_arn     = aws_dms_replication_instance.lab.replication_instance_arn
    dms_secrets_role_arn = aws_iam_role.dms_secrets.arn
    source               = { host = aws_rds_cluster.db["source"].endpoint, port = 3306, master_secret_arn = aws_rds_cluster.db["source"].master_user_secret[0].secret_arn, dms_secret_arn = aws_secretsmanager_secret.dms["source"].arn }
    target               = { host = aws_db_instance.target.address, port = 5432, master_secret_arn = aws_db_instance.target.master_user_secret[0].secret_arn, dms_secret_arn = aws_secretsmanager_secret.dms["target"].arn }
  }
}
