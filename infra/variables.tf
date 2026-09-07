variable "expected_account_id" {
  description = "Required sandbox AWS account. Provider refuses any other account."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "Provide a 12 digit sandbox account ID."
  }
}
variable "region" {
  type    = string
  default = "us-east-1"
}
variable "name" {
  type    = string
  default = "hydra-practice"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,25}$", var.name))
    error_message = "Use 3-26 lowercase letters, digits, or hyphens; start with a letter."
  }
}
variable "mysql_engine_version" {
  description = "Choose an available Aurora MySQL 3.x version after the preflight."
  type        = string
}
variable "postgres_engine_version" {
  description = "Choose an available Aurora PostgreSQL 17.x version after the preflight."
  type        = string
}
variable "db_instance_class" {
  type    = string
  default = "db.r6g.large"
}
variable "dms_engine_version" {
  type    = string
  default = "3.5.4"
}
variable "create_dms_service_roles" {
  description = "Set false when the account already has dms-vpc-role and dms-cloudwatch-logs-role."
  type        = bool
  default     = true
}
variable "add_readers" {
  description = "Add one reader per Aurora cluster for failover practice."
  type        = bool
  default     = false
}
variable "deletion_protection" {
  type    = bool
  default = true
}
variable "owner_label" {
  description = "Lab owner identifier; do not put personal contact details here."
  type        = string
  default     = "instructor"
}
variable "review_after" {
  description = "UTC cost-review deadline. A tag is not an automatic shutdown."
  type        = string
  default     = "manual-review-required"
}
