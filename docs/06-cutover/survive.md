# Diagnose a failed cutover

Practice on your own disposable lab. Do not damage a completed customer migration.
If target readiness fails, leave gateway stopped and inspect target logs with
`docker compose logs --tail=50 target`. Check the target DB instance endpoint, TLS CA,
SQL grants, native schema and unchanged shared secrets from task 2.

A return to source is only safe if you can prove **no target writes occurred**.
Target startup itself may write state. If that proof is unavailable, keep traffic
fenced and recover forward. Do not equate an unsuccessful browser login with an
unchanged target database.

For a deliberate abort **before target was ever started**, on the runner:

```bash
docker compose up -d --no-deps source
```

```bash
curl -fsS http://127.0.0.1:4445/health/ready
```

```bash
printf '{"active":"source"}\n' > runtime/active.json
```

```bash
printf 'upstream hydra_active { server source:4444; }\n' > runtime/upstream.conf
```

```bash
docker compose up -d --no-deps gateway
```

Verify Alice's login/refresh on source. If DMS was stopped after a valid drain and
the required binlogs remain available, use the [resume exercise](../07-incidents/build.md)
to resume CDC from its checkpoint for the next cutover attempt. Do not reload a
populated target blindly.

**Evidence:** failure cause, proof of the recovery boundary, corrected setting,
restored application behavior and the next rehearsal plan.
