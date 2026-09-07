# Recover a stopped source service

**Scenario:** the gateway is up, but the authentication service is unavailable. Use only the dedicated practice Compose project.

On **Laptop**, as **your user**:

```bash
.venv/bin/python scripts/chaos.py inject source-down
```

Try to sign in. Observe the difference between a page served by the portal and an OAuth request that requires Hydra. Inspect container status and recent source logs.

Your task is to restore the missing service without deleting volumes, rotating secrets, or registering a new client. The fix should preserve the existing authentication state.

After applying your fix, on **Laptop**, as **your user**:

```bash
.venv/bin/python scripts/chaos.py validate source-down
```

Validation must report source readiness and a working portal. Then refresh your preexisting browser session: health checks alone do not prove token continuity.

**Record:** first symptom, diagnosis, exact corrective action, and verification. Use `scripts/chaos.py recover source-down` only if you need the instructor recovery path.
