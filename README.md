# Hydra MySQL to PostgreSQL Migration Practice Lab

A six-task practice lab built around a Comcast training story. The student creates
Aurora MySQL and RDS for PostgreSQL, restores supplied synthetic MySQL data,
installs Hydra, assesses conversion with AWS SCT, configures DMS full load and
CDC, validates data, cuts over the application and removes the lab.

Start with the [published customer guide](https://hapi-suta.github.io/laas-hydra-migration-lab/)
or [local guide source](docs/index.md). AWS Console is the primary path, followed by the native CLI alternative. SQL/application steps are shown explicitly. Nothing is
pre-provisioned for the student by following or opening the guide.

The restore fixture includes schema and synthetic rows. The full profile expands
to at least 35 GiB of logical client content. It compresses heavily and is not a
production performance distribution. The learner creates real OAuth state through
the portal after restoration. See the [validation record](VALIDATION.md) for
executed tests and their limits.

Hydra v2.2.0 is the pinned open-source practice baseline. Confirm the customer's
actual version before treating results as a customer migration plan.

## Repository contents

| Path | Purpose |
|---|---|
| docs/ | Student guides, AWS references and explicit checkpoints |
| app/ | Synthetic login/consent portal and protected account page |
| compose.cloud.yaml | Application container definitions used on the student's runner |
| migration/ | Complete example DMS table mappings and task settings |
| scripts/ | Site builder and optional authoring/verification tools |
| infra/ | Optional engineering references, outside the student setup path |
| tests/ | Migration utility checks and published-guide checks |
| runtime/, evidence/, artifacts/ | Ignored private authoring files, execution reports and release build assets |

## Build the website locally

Install the Python requirements, then run:

```bash
python3 scripts/build_site.py
```

```bash
python3 -m unittest discover -s tests -v
```

```bash
python3 -m http.server 8000 --directory site
```

The GitHub Actions workflow builds, checks and deploys the site from main. The
source bundle uses an explicit file allowlist and excludes credentials, runtime
state, database contents and Terraform state. Restore fixtures are separate release
assets with manifests and SHA-256 checksums.
