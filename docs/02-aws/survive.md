# Diagnose infrastructure and connection failures

| Symptom | What to inspect | Next action |
|---|---|---|
| SSM Connect unavailable | Instance role, agent, public IP, runner default route | Correct the missing prerequisite in Module 02; confirm Online |
| MySQL timeout | Writer endpoint, source SG, runner subnet routes | Restore only the required 3306 rule/path |
| PostgreSQL timeout | Peering Active, routes both ways, target SG 5432 | Correct the missing return route or SG reference |
| TLS error | Native hostname and CA file readability inside container | Correct the endpoint/CA; keep verification enabled |
| DMS cannot read secret | Dedicated role trust, two secret ARNs, interface endpoint and 443 rule | Correct the failing IAM/network layer and retest |
| Writer stays Creating | RDS Events and describe-db-instances | Wait or resolve the reported error; do not duplicate the cluster |

Use the [application TLS connection commands](application.md) to verify both
engines directly before troubleshooting DMS. Record engine identity and TLS cipher.
Follow the [controlled DMS network incident](../07-incidents/build.md#4-remove-only-the-dms-source-network-rule)
only after you have a healthy baseline.

**Gate:** explain the failed layer, save the correction and prove both TLS clients
and DMS endpoint tests succeed. Infrastructure availability alone is insufficient.
