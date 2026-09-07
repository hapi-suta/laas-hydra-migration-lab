# Assess the schema with the SCT GUI

**Environment:** AWS Console for endpoint/secret lookup, AWS SCT desktop GUI on a
supported Windows or Linux workstation, and private database connectivity.
**CLI counterpart:** [SCT and schema preparation](build.md).

SCT's desktop GUI is a separate application. **DMS Schema Conversion** in the AWS
Console is another service with its own configuration and support matrix; it is
not the SCT desktop application. This exercise specifically produces an SCT
assessment and compares it with Hydra's native PostgreSQL schema.

## 1. Install and configure the tools

1. Use the [official SCT installation guide](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Installing.html)
   to download the appropriate Windows/Linux package and verify the distribution.
   The current desktop support list does not include macOS; a Mac user can use
   the runner CLI path or a supported workstation for GUI practice.
2. Install the official MySQL Connector/J and PostgreSQL JDBC drivers. Open
   **SCT → Settings → Global settings → Drivers**, browse to each JAR, and save.
   Record the SCT build and driver versions in your evidence.
3. Open **RDS → Databases** in the AWS Console. Record the two cluster **writer
   endpoints**, ports and target comparison database `sct_compare`. Do not choose
   the application target database `hydra` for applying converted SQL.

## 2. Establish private, verified connections

Use the two [SSM remote-host tunnels](build.md#2-connect-sct-to-the-private-databases)
from the CLI path. Keep them open in separate workstation terminals. Use the
instructor-prepared RDS trust store and TLS configuration; do not disable
certificate checks.

For hostname verification through the tunnels, the instructor can map the **exact
native RDS endpoint names** to `127.0.0.1` in the workstation's hosts file, while
SCT uses those native names with local ports 13306 and 15432. The SSM remote-host
parameters still name the real remote endpoints, which the runner resolves in
AWS. This keeps the certificate hostname intact. Record and remove the temporary
workstation mappings when finished. Do not change Route 53 or AWS DNS records.

Alternatively, run SCT on an authorized workstation with private network access
and use native endpoints on ports 3306/5432 directly. Verify the network path
before entering credentials.

## 3. Create the project and source connection

1. In SCT choose **File → New project**, name it with the lab prefix, and save it
   in your private working directory.
2. Choose **Add source → MySQL → Next**.
3. Enter a connection name such as `HYDRA_MYSQL`. Use the native source hostname
   and the applicable direct/tunnel port.
4. Enter the dedicated `sct_reader` credential supplied privately by bootstrap.
   It has SELECT and SHOW VIEW access for this isolated lab. Do not use the DMS
   replication user as a substitute for SCT's required privileges.
5. Select **Use SSL**. On the SSL tab select **Require SSL** and **Verify server
   certificate**, and select the instructor-prepared trust store containing the
   applicable RDS CA certificates. Leave password storage disabled unless your
   organization's workstation policy explicitly allows SCT's vault.
6. Choose **Test Connection**; require success, then **Connect**.
[AWS's MySQL SCT connection fields](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Source.MySQL.html).

## 4. Add the comparison target and mapping

1. Choose **Add target → Amazon Aurora PostgreSQL**.
2. Enter a distinct connection name such as `SCT_COMPARE`, native target writer
   hostname, direct/tunnel port, and database **sct_compare**.
3. Use the lab's schema-owner credentials and the JDBC driver's verified TLS
   settings/trust store. This role must be able to create objects in sct_compare.
4. Test the connection and connect. Inspect the target tree to ensure it is the
   comparison database.
5. In the source tree, select only the `hydra` database/schema. Add a mapping to
   the comparison target. Exclude unrelated MySQL system schemas from conversion.

## 5. Generate and inspect the assessment

1. Select the source `hydra` node and choose **Create report** from its context
   menu. Open the **Assessment report** view.
2. Inspect the summary and **Action items**. For every item, record its object,
   severity, explanation and proposed resolution. A high automatic-conversion
   percentage does not prove Hydra compatibility.
3. Save/export the report as PDF and CSV to private evidence. Record the SCT
   build, driver versions, engine versions, source selection and generation time.

## 6. Convert and compare

1. Select the source `hydra` node → **Convert schema**. Inspect converted objects
   in the target tree, including inline comments/action items.
2. Use **Save as SQL** on the converted target objects. Review the SQL before
   **Apply to database**. Confirm the connection is **sct_compare** and that no
   selected operation targets the application's `hydra` database.
3. Apply the reviewed comparison conversion. Inspect objects and any conversion
   errors in the GUI; retain failed action items rather than suppressing them.
4. Compare the result to the native `hydra.public` schema using the runner's
   inventory and SQL catalog checks. Specifically inspect UUIDs versus strings,
   booleans versus integers, JSONB, timestamp precision, keys/indexes, defaults,
   network IDs and migration bookkeeping.
5. Complete the discrepancy worksheet: object, source, SCT result, native Hydra
   target, chosen decision, reason, and verification. Resolve every migration-
   relevant discrepancy before approving DMS mappings.

## 7. Prepare the real migration target

Return to the runner's Session Manager terminal and follow the inventory review,
mapping generation, LOB scan and guarded target-seed preparation in the
[CLI build](build.md#4-approve-the-inventory-and-generate-mappings). The real
target is initialized by the pinned Hydra migrations, with its native migration
history preserved. Target Hydra remains stopped until cutover.

**Evidence:** successful source/target connection tests, saved SCT project,
assessment PDF/CSV, conversion SQL, action-item resolutions, schema discrepancy
worksheet, reviewed exact mappings, passing LOB and empty-target checks. GUI steps
are documented from AWS references; a CLI-generated report does not prove that
the separate GUI walkthrough was personally replayed.
