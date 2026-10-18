output "alb_security_group_id" {
  description = "Set ingress.securityGroupId in the API Helm values."
  value       = module.api_boundary.alb_security_group_id
}
