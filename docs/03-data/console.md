# Create and inspect data from the Console

**Environment:** AWS Console → EC2 → your runner. **CLI equivalent:** [Create
scale and activity](build.md). **Prerequisite:** cloud portal login passes.

## 1. Open the runner terminal

1. Confirm your account and region. In **EC2 → Instances**, filter by your lab's
   `Project` tag and select its runner.
2. Choose **Connect → Session Manager → Connect**.
3. In the browser terminal, as **ssm-user**, switch users:

```bash
sudo su - ec2-user
```

4. As **ec2-user**, enter the project:

```bash
cd /opt/hydra-practice
```

Aurora's Console does not have a button that generates Hydra records. You execute
the same reviewed generator in this browser-based terminal, then inspect resource
behavior in RDS/CloudWatch. Do not insert fake token signatures by hand.

## 2. Prove a small dataset first

In the **Runner browser terminal**, as **ec2-user**:

```bash
.venv/bin/python scripts/oauth_probe.py login
```

Require `pass: true`. The cookie stays in a private runtime file. Next:

```bash
.venv/bin/python scripts/scale.py --gib 0.05
```

Require `meets_goal: true` and inspect `evidence/scale.json`. Next:

```bash
.venv/bin/python scripts/workload.py --seconds 60 --workers 2 --rps 2
```

Require successful token and client cycles, with zero errors. Correct failures
before the large run; a partial workload is not a pass.

## 3. Run and measure the full profile

In the **Runner browser terminal**, as **ec2-user**:

```bash
.venv/bin/python scripts/scale.py --gib 35 --full-scale --metadata-bytes 16000
```

`--gib 35` sets the logical-byte target. `--full-scale` explicitly permits a large
run. The metadata setting controls the approximate size of each synthetic client's
metadata. Keep the session open until completion; do not start a second generator
against the same prefix. If interrupted, first confirm the earlier process ended,
then rerun to resume. Save the measured report; Aurora volume size is not a
substitute for this logical-byte count.

Run API traffic in a second Session Manager terminal using the workload command
and duration specified by your instructor. Preserve a pre-migration login session
for cutover and record the start/end times of the workload.

## 4. Watch database behavior

1. Open **RDS → Databases → source writer → Monitoring** in another Console tab.
   Inspect CPU, database connections, memory and read/write activity during load.
2. Open **CloudWatch → Metrics → All metrics → RDS**. Select the source writer
   dimension for instance metrics and the source cluster dimension for
   `VolumeBytesUsed`, `VolumeReadIOPs` and `VolumeWriteIOPs` where available.
3. Use a one-minute period and the load's time range. Capture metric names, units,
   dimension, statistic and timestamps with the graph. Avoid comparing cluster
   volume bytes to generator logical bytes as if they were the same measurement.
4. If resource pressure is sustained, stop the generator cleanly in its terminal,
   investigate, and agree a sizing/rate change. Do not disable TLS or integrity
   checks to raise throughput.

**Evidence:** real OAuth/workload results, logical size ≥35 GiB, per-table
distribution and LOB scan, elapsed time, and RDS/CloudWatch observations.
