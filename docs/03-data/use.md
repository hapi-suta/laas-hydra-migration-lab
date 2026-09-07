# Prove your restored source works

1. Save the restore manifest and compare exact client counts and byte totals using
   [the source SQL checks](build.md#4-verify-the-restore-before-starting-hydra).
2. Open your portal tunnel and perform [Alice and Bob login, refresh and revocation](build.md#6-create-actual-oauth-state-through-the-browser).
3. Run source token-table counts before and after those actions. Record counts
   without recording token values.
4. In RDS Monitoring, record CPU, connections and storage I/O during the restore
   and during interactive application use. Explain the difference.

**Gate:** the student restored the data, the manifest matches, and the application
reads and writes the restored database. A download or Available cluster is not
completion evidence.
