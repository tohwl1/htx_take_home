variable "region" {
  description = "AWS region containing the existing EKS/VPN platform."
  type        = string
  default     = "ap-southeast-1"
}
variable "environment" {
  description = "Environment label applied to managed resources."
  type        = string
  default     = "eks"
  validation {
    condition     = contains(["eks", "dev", "staging", "production"], var.environment)
    error_message = "Use eks, dev, staging or production."
  }
}
variable "vpc_id" {
  description = "Existing VPC ID containing the private ALB and EKS pod network."
  type        = string
}
variable "node_security_group_id" {
  description = "Existing security group that protects the API pod IP targets."
  type        = string
}
variable "vpc_cidr" {
  description = "Existing IPv4 pod/VPC network permitted as ALB backend destination."
  type        = string
  validation {
    condition     = can(cidrnetmask(var.vpc_cidr)) && try(tonumber(split("/", var.vpc_cidr)[1]) >= 16, false)
    error_message = "Use the existing IPv4 VPC CIDR, /16 or narrower."
  }
}
variable "on_premise_cidr" {
  description = "Approved on-premise IPv4 source network routed over VPN."
  type        = string
  validation {
    condition     = can(cidrnetmask(var.on_premise_cidr)) && try(tonumber(split("/", var.on_premise_cidr)[1]) >= 16, false)
    error_message = "Use an approved on-premise IPv4 network, /16 or narrower."
  }
}
