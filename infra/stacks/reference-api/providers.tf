provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = "hce-reference-api", Environment = var.environment, ManagedBy = "terraform" }
  }
}
