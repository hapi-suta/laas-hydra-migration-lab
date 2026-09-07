# Hydra Aurora Migration Practice Lab

A customer-operated **Concepts → Build → Use → Survive** lab: run Hydra on MySQL,
generate a measured dataset, assess schema conversion with SCT, migrate through
AWS DMS to Aurora PostgreSQL, and prove authentication continuity.

## Start here

- Customer guide: [docs/index.md](docs/index.md)
- Local rehearsal: `python3 scripts/lab.py init`, then `python3 scripts/lab.py up`
- Build the guide site: `python3 scripts/build_site.py`
- Preview: `python3 -m http.server 8000 --directory site`
- AWS foundation: [infra/README.md](infra/README.md)
- Verification record: [VALIDATION.md](VALIDATION.md)

The local MySQL/PostgreSQL environment is for authoring and introductory practice.
SCT/DMS exercises run against real AWS Aurora. Local database copying is not a
substitute for the cloud migration exercise.

Hydra `v2.2.0` is a provisional **open-source demo baseline**, not a claim about the
customer's release or a recommendation to upgrade/downgrade their service. Confirm
the customer's version before treating results as production evidence.

## Files

| Path | Role |
|---|---|
| `docs/` | Customer learning journey |
| `app/` | Synthetic login/consent portal and protected account page |
| `compose.yaml` | Local source, target, and stable issuer gateway |
| `scripts/` | Setup, API workloads, inventory, mapping, reconciliation, evidence |
| `infra/` | AWS VPCs, Aurora, DMS instance, and SSM lab runner |
| `migration/` | DMS task policies and mapping outputs |
| `tests/` | Checks for migration gates, site, and application helpers |
| `runtime/` | Ignored local credentials and transient state |
| `evidence/` | Ignored execution reports; reviewed summary in VALIDATION.md |

Guides never embed customer credentials. Keep generated runtime files and raw
token evidence private. The demo identities are synthetic; do not connect this
portal to production identity systems.
