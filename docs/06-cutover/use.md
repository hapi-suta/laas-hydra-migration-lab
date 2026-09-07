# Prove the application survived

1. Refresh the pre-cutover session without starting a new authorization flow. Explain what state this exercises.
2. Sign in as Bob after cutover. Confirm new PostgreSQL writes work.
3. Revoke a target-issued token and prove it cannot be used again.
4. Compare issuer and JWKS before and after. Explain which changes would invalidate relying-party assumptions.
5. Identify the exact instant after which switching back to MySQL would lose target-side changes.

**Gate:** save a matrix of old access token, old refresh token, new login, client authentication, revocation, and subject consistency. Record actual outcomes, not intended outcomes. Investigate any failure before marking the migration successful.
