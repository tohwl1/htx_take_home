resource "aws_security_group" "alb" {
  # checkov:skip=CKV2_AWS_5:Attached by the AWS Load Balancer Controller through the reviewed Helm ingress security-groups annotation; Terraform exports its ID.
  name_prefix = "${var.name}-alb-"
  description = "Internal API ALB: HTTPS from approved on-premise network only"
  vpc_id      = var.vpc_id
  lifecycle {
    create_before_destroy = true
  }
  tags = { Name = "${var.name}-alb" }
}

resource "aws_vpc_security_group_ingress_rule" "on_premise_https" {
  security_group_id = aws_security_group.alb.id
  description       = "On-premise API clients through VPN"
  cidr_ipv4         = var.on_premise_cidr
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "api_tls" {
  security_group_id = aws_security_group.alb.id
  description       = "TLS to API pod targets in VPC"
  cidr_ipv4         = var.vpc_cidr
  from_port         = 8443
  to_port           = 8443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "node_api_tls" {
  security_group_id            = var.node_security_group_id
  referenced_security_group_id = aws_security_group.alb.id
  description                  = "TLS from internal API ALB to pod IP targets"
  from_port                    = 8443
  to_port                      = 8443
  ip_protocol                  = "tcp"
}
