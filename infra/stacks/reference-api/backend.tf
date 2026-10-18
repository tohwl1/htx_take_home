terraform {
  # Assume this remote state bucket already exists and is platform-managed.
  # Dummy name/account: replace or override before any remote initialization.
  backend "s3" {
    bucket       = "hce-terraform-state-000000000000-ap-southeast-1"
    key          = "hce/eks/api-boundary.tfstate"
    region       = "ap-southeast-1"
    encrypt      = true
    use_lockfile = true
  }
}
