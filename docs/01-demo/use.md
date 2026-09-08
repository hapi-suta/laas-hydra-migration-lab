# Explain what each component does

Before building, identify where each action belongs:

| Action | Component |
|---|---|
| Create the source cluster and target DB instance | RDS Console or AWS CLI |
| Import the supplied logical SQL | MySQL client on your runner |
| Assess/convert schema | AWS SCT desktop or batch CLI |
| Move existing rows and subsequent changes | AWS DMS full load and CDC |
| Prove old refresh tokens still work | Hydra and the practice portal |
| Verify completion and diagnose lag | SQL, DMS statistics and CloudWatch |

**Gate:** explain why SCT conversion, a completed full load and a successful
application cutover are three different results.
