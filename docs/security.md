# Task 5: three security risks and controls

1. **Stolen credentials.** A stolen token lets an attacker impersonate the
   on-premise application. The API reads its token from an external Kubernetes
   Secret, not Git or Helm values. Operators must restrict Secret access, encrypt
   secrets at rest and rotate the token by updating the Secret and restarting all
   replicas. The shared token lacks expiry and individual revocation. The target
   uses short-lived IdP tokens with issuer, audience, expiry and `reference:read`
   checks; the IdP owns signing keys. For batch uploads, the design uses Roles
   Anywhere with organisation-issued certificates and scoped temporary credentials;
   the on-premise operator must protect and rotate the uploader's private key.

2. **Excessive network access.** An overly broad firewall rule could expose the
   API to unauthorized systems. Terraform permits ALB ingress on TCP 443 from the
   approved on-premise CIDR and backend TCP 8443 from the ALB security group to the
   existing target security group. The chart specifies an internal ALB and default-deny
   NetworkPolicies with explicit allowances. Platform owners must verify VPN
   routes, policy enforcement and existing security-group rules; the chart still
   permits the configured VPC and monitoring namespace to reach the API port.
   The batch design uses private endpoints and a private database, without inbound
   internet access to the on-premise VM.

3. **Data interception.** Unencrypted connections could expose reference data,
   transactions or credentials. The design uses IPsec VPN plus HTTPS to the API
   and S3, and verified TLS from the batch worker to PostgreSQL. ACM manages the
   ALB frontend certificate; platform PKI issues backend certificates, whose private
   keys stay in restricted TLS Secrets. Operators own renewal and distribution of
   trusted CA bundles. ALB re-encrypts traffic but does not validate backend
   certificates; stronger backend identity needs an additional verified proxy or
   mesh. The API chart exports traces over HTTPS using a mounted CA; platform
   owners must secure downstream telemetry. Live TLS checks remain outstanding.

Batch controls and IdP integration describe the target design. They are not
implemented by the selected Terraform slice.
