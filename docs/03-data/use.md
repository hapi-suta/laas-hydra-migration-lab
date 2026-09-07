# Explore your dataset

1. Compare logical payload bytes, table/index allocation, and Aurora cluster storage. Explain why they differ.
2. Stop the scale process between batches, rerun, and confirm generated IDs remain unique and the final size meets the goal.
3. Compare the data produced by client-credentials traffic with the data produced by browser authorization-code login.
4. Increase workload concurrency modestly, then compare requested rate, successful operations, database CPU, and errors.
5. Identify which tables contain references to the network ID. Explain why changing every `nid` randomly would break this demo.

<details markdown="1"><summary>Hint: use inventory as evidence</summary>

On **Runner**, as **ec2-user**:

```bash
.venv/bin/python scripts/inventory.py
```

Inspect exact counts and columns in `evidence/inventory.json`. Do not assume every required table starts with `hydra_`.

</details>

**Gate:** describe the dataset's limitations honestly and show the final measured size. Do not call random metadata “production data.”
