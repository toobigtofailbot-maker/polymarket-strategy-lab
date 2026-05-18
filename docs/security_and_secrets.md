# Security And Secrets

- No API keys in the repository.
- No private keys in the repository.
- No mnemonic phrases in the repository.
- No real wallet addresses unless explicitly marked public and non-secret.
- No secrets in logs.
- No secrets in tests.
- No secrets in docs.
- Use `.env` locally, but never commit it.
- Use environment variables or an approved secret manager later.
- Secret scanning is required before merge.

## Incident Response

If a secret leaks, stop work, revoke or rotate the credential, remove it from the working tree, document the incident, and require human review before continuing.

