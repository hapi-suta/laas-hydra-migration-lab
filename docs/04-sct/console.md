# Assess the schema with the SCT GUI

**Environment:** AWS Console for endpoint/secret lookup, AWS SCT desktop GUI on a
supported Windows or Linux workstation, and private database connectivity.
**CLI counterpart:** [SCT and schema preparation](build.md).

SCT's desktop GUI is a separate application. **DMS Schema Conversion** in the AWS
Console is another service with its own configuration and support matrix; it is
not the SCT desktop application. This exercise specifically produces an SCT
assessment and compares it with Hydra's native PostgreSQL schema.

## 1. Install SCT and the JDBC drivers yourself

1. Open the [AWS SCT installation procedure](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Installing.Procedure.html).
2. On a supported Windows workstation, download the Windows ZIP, extract it,
   launch the MSI, accept the license and complete the installer. On Ubuntu or
   Fedora, download the matching package and use the exact dpkg/rpm installation
   command on that AWS page. Native macOS is not on the desktop support list;
   use the [runner CLI lesson](build.md) or a supported workstation.
3. Follow [AWS package verification](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Installing.InstallValidation.html).
   For Windows, inspect the MSI digital signature before installing. Record the
   installed SCT build from **Help → About**.
4. Download MySQL Connector/J and PostgreSQL JDBC JARs from the links in
   [CLI step 1](build.md#1-install-java-sct-and-both-jdbc-drivers). Extract the
   MySQL distribution if downloading its ZIP from the vendor site.
5. In **SCT → Settings → Global settings → Drivers**, choose the MySQL and
   PostgreSQL driver files, then save. Record both driver versions.
6. In RDS, record your two cluster writer endpoints. The comparison target
   database is **sct_compare**, which you created in Module 02.

## 2. Create your trust store and private connections

Create the RDS trust store yourself using [CLI step 2](build.md#2-build-your-rds-trust-store).
The Linux commands can run on your supported Linux workstation. For Windows,
use the runner to create the public-CA JKS, then transfer it to your workstation
using Session Manager's file text route below. This file contains public
certificates, not private keys or database credentials.

On the runner, run `base64 -w0 runtime/sct/rds-trust.jks`. Copy the single line
into a local file named `rds-trust.b64` using Notepad. In **Windows PowerShell**, in
that file's directory, decode it:

```powershell
[IO.File]::WriteAllBytes("$PWD\rds-trust.jks",[Convert]::FromBase64String((Get-Content .\rds-trust.b64 -Raw)))
```

Record the trust-store password you chose. In SCT **Settings → Global settings →
Security → Trust store → Select existing trust store**, add/import your `rds-trust.jks` as the trusted store, entering that
password. Choose this store in each connection's SSL settings.
[AWS SCT encrypted RDS connections](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Source.Encrypt.RDS.html).

From two separate authenticated **workstation terminals**, start the tunnels:

```bash
aws ssm start-session --region us-east-1 --target YOUR_RUNNER_INSTANCE_ID --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{"host":["YOUR_SOURCE_WRITER_ENDPOINT"],"portNumber":["3306"],"localPortNumber":["13306"]}'
```

```bash
aws ssm start-session --region us-east-1 --target YOUR_RUNNER_INSTANCE_ID --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{"host":["YOUR_TARGET_WRITER_ENDPOINT"],"portNumber":["5432"],"localPortNumber":["15432"]}'
```

Replace all three placeholders in each command. Windows users can execute these
in a Bash-compatible AWS CLI terminal, or put the parameters JSON in a local file
and pass `--parameters file://source-tunnel.json` / `target-tunnel.json` from
PowerShell. Each JSON file contains the corresponding object shown above.
Keep both tunnels open. Free local ports 13306/15432 first if already occupied.
[AWS remote-host port forwarding](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html).

For verified hostnames, edit your **workstation** hosts file as administrator:
Windows `C:\Windows\System32\drivers\etc\hosts` with elevated Notepad, or
Linux `/etc/hosts` with `sudo vi /etc/hosts`. Add these two lines with the exact
native endpoint names from RDS:

```text
127.0.0.1 YOUR_SOURCE_WRITER_ENDPOINT
127.0.0.1 YOUR_TARGET_WRITER_ENDPOINT
```

SCT then uses those native names on local ports 13306 and 15432. The runner still
resolves the real endpoints in AWS for the remote side of each tunnel. Remove
these two workstation entries after SCT practice. Do not change Route 53 records
or disable certificate checking to resolve a hostname mismatch.

## 3. Create the project and source connection

1. In SCT choose **File → New project**, name it with the lab prefix, and save it
   in your private working directory.
2. Choose **Add source → MySQL → Next**.
3. Enter a connection name such as `HYDRA_MYSQL`. Use the native source hostname
   and the applicable direct/tunnel port.
4. Enter the dedicated `sct_reader` credential you created in Module 02.
   It has SELECT and SHOW VIEW access for this isolated lab. Do not use the DMS
   replication user as a substitute for SCT's required privileges.
5. Select **Use SSL**. On the SSL tab select **Require SSL** and **Verify server
   certificate**, and select the trust store you created in step 2 containing the
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

Return to the runner and complete [the native SQL schema checks](schema-checks.md):
inventory, action-item worksheet, maximum LOB scan and guarded removal of the
unused target network seed. You execute and inspect every SQL statement yourself.
The PostgreSQL migration history remains intact; target Hydra stays stopped.

**Evidence:** successful source/target connection tests, saved SCT project,
assessment PDF/CSV, conversion SQL, action-item resolutions, schema discrepancy
worksheet, reviewed exact mappings, passing LOB and empty-target checks. GUI steps
are documented from AWS references; a CLI-generated report does not prove that
the separate GUI walkthrough was personally replayed.
