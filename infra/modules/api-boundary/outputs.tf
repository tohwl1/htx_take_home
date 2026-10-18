output "alb_security_group_id" {
  description = "Dedicated security group attached to the internal API ALB by Helm."
  value       = aws_security_group.alb.id
}
