# Prove normal authentication behavior

## Exercise 1 — Two identities

Sign in as Alice in one browser profile and Bob in another. Compare the introspected subjects. Explain why the portal's browser cookie and Hydra's database token state are different things.

## Exercise 2 — Token lifecycle

Refresh Alice's session twice, then revoke and sign out. Attempt to reopen the protected page. Record the behavior before and after revocation without recording token strings.

## Exercise 3 — Follow a request

Identify which service handles the login page, consent acceptance, token exchange, and introspection. Inspect `app/nginx.conf` and `app/server.py` after making your prediction.

## Exercise 4 — Restart versus reset

Stop and start the gateway with Docker Compose. Explain why this should preserve database state and why deleting database volumes would not.

<details markdown="1"><summary>Hint: inspect the lifecycle commands</summary>

On **Laptop**, as **your user**:

```bash
python3 scripts/lab.py status
```

Compare long-running services with successful one-shot migration containers. Read `compose.yaml` to locate named database volumes.

</details>

**Gate:** demonstrate successful source login, refresh, and revoke. Save a short explanation of each service's role before proceeding to AWS.
