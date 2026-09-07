# Trace and verify the network

1. Explain the full path from DMS to the MySQL writer. Identify both route tables and the matching security-group rule.
2. Explain how your laptop reaches the portal despite the runner having no inbound security-group rules.
3. Locate the AWS-managed administrator secrets and the empty DMS endpoint secrets. Explain why they have different consumers.
4. Identify each cluster's writer endpoint and distinguish it from a reader endpoint.
5. Estimate a full day of charges using the current AWS pricing calculator, including database instances, DMS, EC2, endpoint hours, storage, I/O, and retained snapshots.

<details markdown="1"><summary>Verification hint</summary>

Use the AWS console to inspect actual routes and security-group references; a worksheet is intended state, not proof of the deployed state. Use the runner's TLS database connection and capture the engine identity and encryption status.

</details>

**Evidence:** a network sketch with source/target direction, chosen engine versions, SSM screenshot, and a cost worksheet.
