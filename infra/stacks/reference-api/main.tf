module "api_boundary" {
  source                 = "../../modules/api-boundary"
  vpc_id                 = var.vpc_id
  vpc_cidr               = var.vpc_cidr
  on_premise_cidr        = var.on_premise_cidr
  node_security_group_id = var.node_security_group_id
  name                   = "hce-api-${var.environment}"
}
