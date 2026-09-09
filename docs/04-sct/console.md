# Assess the schema with the SCT GUI

**Environment:** AWS Console for endpoint/secret lookup, AWS SCT desktop GUI on
your Windows EC2 desktop opened from the Mac, and private database connectivity.
Create that desktop with the [Mac-to-Windows setup lesson](mac-desktop.md) first.
**CLI counterpart:** [SCT and schema preparation](build.md).

SCT's desktop GUI is a separate application. **DMS Schema Conversion** in the AWS
Console is another service with its own configuration and support matrix; it is
not the SCT desktop application. This exercise specifically produces an SCT
assessment and compares it with Hydra's native PostgreSQL schema.

## 1. Install SCT and the JDBC drivers yourself

- Open the [AWS SCT installation procedure](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Installing.Procedure.html).
- In Edge inside your Windows EC2 desktop, download the Windows ZIP. In File
   Explorer, open Downloads, right-click the ZIP and choose **Extract All**. Open
   the extracted folder and locate its MSI. These actions happen on Windows;
   your Mac displays that desktop.
- Follow [AWS package verification](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Installing.InstallValidation.html).
   Right-click the MSI → **Properties → Digital Signatures**. Select the Amazon
   Web Services signer and open **Details**; require that the signature is OK.
   Then launch the MSI, read the license and complete the installer. Open SCT
   from its desktop shortcut. Allow a few minutes for the first launch; do not
   open more copies while it starts. If it offers **Get started with DMS SC**,
   choose **Not now** to continue with this SCT desktop exercise. Record the
   build from **Help → About**.
- Download the [MySQL Connector/J JAR](https://repo.maven.apache.org/maven2/com/mysql/mysql-connector-j/26.7.0/mysql-connector-j-26.7.0.jar) and [PostgreSQL JDBC JAR](https://jdbc.postgresql.org/download/postgresql-42.7.13.jar) to a folder inside Windows. Keep the `.jar` files; SCT opens them directly.
- In **SCT → Settings → Global settings → Drivers**, choose the MySQL and
   PostgreSQL driver files, then save. Record both driver versions.
- In RDS, record your source cluster writer endpoint and target DB instance endpoint. The comparison target
   database is **sct_compare**, which you created in task 2.

## 2. Create your trust store and private connections

The trust store tells SCT which database certificates to trust. Create it on the runner, then copy its public certificates to your workstation. It contains no database password.

In the AWS Console, open **EC2 → Instances → your runner → Connect → Session Manager → Connect**. Run:

```bash
sudo su - ec2-user
cd /opt/hydra-practice
sudo dnf install -y java-17-amazon-corretto-headless
mkdir -p runtime/sct
chmod 700 runtime/sct
```

**Expected:** Java installs successfully. The directory and permission commands normally print nothing when they succeed.


Download the public regional CA bundle:

```bash
curl -fL https://truststore.pki.rds.amazonaws.com/us-east-1/us-east-1-bundle.pem -o runtime/sct/rds-region.pem
```

Split the PEM bundle into individual certificates. This awk command copies each
complete certificate to its own file; it does not contact a database:

```bash
awk '/-----BEGIN CERTIFICATE-----/{n++; f=sprintf("runtime/sct/ca-%d.pem",n)} f{print > f} /-----END CERTIFICATE-----/{close(f); f=""}' runtime/sct/rds-region.pem
```

Choose a long alphanumeric trust-store password privately. Avoid apostrophes
and newlines because the later SCT CLI parameter uses single-quoted text. This protects a store containing public
CA certificates, not database passwords:

```bash
read -rsp 'New SCT trust-store password: ' SCT_TRUST_PASSWORD
```

```bash
export SCT_TRUST_PASSWORD
```

Import every regional certificate into a new JKS store:

```bash
for cert in runtime/sct/ca-*.pem; do
  keytool -importcert -noprompt -alias "$(basename "$cert" .pem)" \
    -file "$cert" -keystore runtime/sct/rds-trust.jks -storetype JKS \
    -storepass:env SCT_TRUST_PASSWORD || break
done
```

```bash
keytool -list -keystore runtime/sct/rds-trust.jks -storepass:env SCT_TRUST_PASSWORD
```

Require one trusted entry per downloaded certificate. If an alias exists from an
earlier attempt, inspect the existing store rather than replacing it blindly.
[AWS RDS CA bundles](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.SSL.html).

On the runner, run `base64 -w0 runtime/sct/rds-trust.jks`. Copy the single line
into a file named `rds-trust.b64` inside the Windows desktop. Open **Windows
PowerShell** there and run:

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\HydraLab" | Out-Null
Set-Location "$HOME\HydraLab"
notepad rds-trust.b64
```

In Notepad, paste the copied base64 line, save the file and close Notepad. Back
in that same PowerShell window, decode it:

```powershell
[IO.File]::WriteAllBytes("$PWD\rds-trust.jks",[Convert]::FromBase64String((Get-Content .\rds-trust.b64 -Raw)))
```

Record the trust-store password you chose. In SCT **Settings → Global settings →
Security → Trust store → Select existing trust store**, add/import your `rds-trust.jks` as the trusted store, entering that
password. Choose this store in each connection's SSL settings.
[AWS SCT encrypted RDS connections](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Source.Encrypt.RDS.html).

### Windows EC2: connect directly through the lab networks

For the Mac route, SCT runs on your Windows EC2 instance in the source VPC.
Use the native Aurora writer hostname on **3306**, and the native RDS PostgreSQL
hostname on **5432**. Select **sct_compare** as the PostgreSQL database. Keep the
RDS trust store and certificate checks enabled. Continue with step 3 below.
Your Mac-to-Windows desktop connection stays open; you do not need a separate
database tunnel or hosts-file edits for this EC2 route.

## 3. Create the project and source connection

- In SCT choose **File → New project**, name it with the lab prefix, and save it
   in your private working directory.
- Choose **Add source → MySQL → Next**.
- Enter a connection name such as `HYDRA_MYSQL`. For the Windows EC2 route,
   use your native source writer hostname and port **3306**.
- Enter the dedicated `sct_reader` credential you created in task 2.
   It has SELECT and SHOW VIEW access for this isolated lab. Do not use the DMS
   replication user as a substitute for SCT's required privileges.
- Select **Use SSL**. On the SSL tab select **Require SSL** and **Verify server
   certificate**, and select the trust store you created in step 2 containing the
   applicable RDS CA certificates. Leave password storage disabled unless your
   organization's workstation policy explicitly allows SCT's vault.
- Choose **Test Connection**; require success, then **Connect**.
[AWS's MySQL SCT connection fields](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Source.MySQL.html).

## 4. Add the comparison target and mapping

- Choose **Add target → Amazon RDS for PostgreSQL**.
   [AWS SCT RDS PostgreSQL walkthrough](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_GettingStarted.SCT.html).
- Enter a distinct connection name such as `SCT_COMPARE`, your native target DB
   instance hostname, port **5432** for Windows EC2, and database **sct_compare**.
- Use the lab's schema-owner credentials and the JDBC driver's verified TLS
   settings/trust store. This role must be able to create objects in sct_compare.
- Test the connection and connect. Inspect the target tree to ensure it is the
   comparison database.
- In the source tree, select only the `hydra` database/schema. Add a mapping to
   the comparison target. Exclude unrelated MySQL system schemas from conversion.

## 5. Generate and inspect the assessment

- Select the source `hydra` node and choose **Create report** from its context
   menu. Open the **Assessment report** view.
- Inspect the summary and **Action items**. For every item, record its object,
   severity, explanation and proposed resolution. A high automatic-conversion
   percentage does not prove Hydra compatibility.
- Save/export the report as PDF and CSV to private evidence. Record the SCT
   build, driver versions, engine versions, source selection and generation time.

## 6. Convert and compare

- Select the source `hydra` node → **Convert schema**. Inspect converted objects
   in the target tree, including inline comments/action items.
- Use **Save as SQL** on the converted target objects. Review the SQL before
   **Apply to database**. Confirm the connection is **sct_compare** and that no
   selected operation targets the application's `hydra` database.
- Complete the [tested export repairs](schema-checks.md#apply-the-corrections-found-in-the-rds-rehearsal)
   before applying. If you edited the exported SQL, use the linked psql procedure
   to apply that exact reviewed file. The GUI target tree does not automatically
   inherit edits made to an exported file. Inspect the resulting objects and
   retain failed action items rather than suppressing them.
- Compare the result to the native `hydra.public` schema using the runner's
   inventory and SQL catalog checks. Specifically inspect UUIDs versus strings,
   booleans versus integers, JSONB, timestamp precision, keys/indexes, defaults,
   network IDs and migration bookkeeping.
- Complete the discrepancy worksheet: object, source, SCT result, native Hydra
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
