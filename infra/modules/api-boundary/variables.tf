variable "name" {
  description = "Resource name prefix."
  type        = string
}
variable "vpc_id" {
  description = "Existing private application VPC."
  type        = string
}
variable "vpc_cidr" {
  description = "Backend pod network destination for HTTPS."
  type        = string
}
variable "on_premise_cidr" {
  description = "Approved on-premise API client source network."
  type        = string
}
variable "node_security_group_id" {
  description = "Existing SG protecting the EKS pod IP targets."
  type        = string
}
