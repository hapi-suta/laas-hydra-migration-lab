# Use SCT's Windows desktop from your Mac

**Start here:** your Mac, after tasks 1 and 2. Your Linux runner and both databases
already exist. Alice's app still uses MySQL.

You will create a temporary Windows EC2 computer, open its desktop on your Mac,
and install SCT there using the [AWS SCT installation procedure](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Installing.Procedure.html).
The databases remain **Aurora MySQL (source)** and **RDS PostgreSQL (target)**.

| Computer | What runs there |
|---|---|
| Your Mac | Browser, Terminal, AWS CLI, Session Manager plugin and Windows App |
| Windows EC2 | SCT desktop and the two JDBC drivers |
| Linux EC2 runner | Hydra, SQL clients and the restore work you already completed |
| Aurora MySQL / RDS PostgreSQL | The source and target databases |

The Windows instance uses the runner's existing subnet, security group and SSM
instance profile. That group already permits private database connections. You
will open its desktop through Session Manager; leave its inbound rules empty.

## 1. Prepare your Mac

- Confirm the [Mac CLI and plugin checks](../workstation.md) passed.
- Open the **Mac App Store**, find **Windows App** published by Microsoft, and
   install it. Open it and finish or skip the introductory tour. For this lab you
   will add a remote PC, rather than a Microsoft cloud workspace.
- In **Finder → Documents**, create a folder named `Hydra-SCT-evidence`.
   This folder will receive your assessment, SQL and screenshots. Keep passwords
   and the EC2 private key outside it.
- Keep your AWS Console open in the assigned account and **us-east-1**.

[Microsoft's Mac remote-PC instructions](https://learn.microsoft.com/en-us/windows-app/get-started-connect-devices-desktops-apps).

## 2. Create the Windows computer

Use the Console path first. The CLI alternative creates the same instance;
choose one route.

<details class="instructions" markdown="1" open>
<summary>AWS Console: create your Windows SCT instance</summary>

- Open **EC2 → Instances**, select your **Linux runner**, and record its subnet
   ID, security-group ID and IAM role from its details. These are resources from
   your own task 1. You will reuse them, while leaving the runner running.
- Choose **Launch instances**. Name the new computer with your prefix plus
   `-sct`, for example `comcast-student-01-sct`.
- In the image selector, choose the Amazon-provided **Microsoft Windows Server
   2022 Base**, **64-bit x86**, with the full desktop. Choose the Base image;
   the Server Core image has no normal desktop. SQL Server is not needed here.
- Choose **t3.large**. This lab uses 8 GiB of memory for the desktop and SCT.
- Under **Key pair**, choose **Create new key pair**. Name it with your prefix
   plus `-sct-key`, select **RSA** and **.pem**, then create it. Save the downloaded
   PEM privately on your Mac. AWS uses this key to decrypt the initial Windows
   password. Record its path; never paste its contents into lab evidence.
- In **Network settings → Edit**, choose your source VPC and the same
   `runner-public` subnet as the Linux runner. Enable the public IP for outbound
   downloads and SSM access. Select **existing security group** and choose the
   runner group. Remove any automatically selected new group or inbound RDP rule.
- Set the root disk to **60 GiB gp3**, encrypted, with **Delete on termination**
   enabled. Record the resulting volume ID after launch.
- Under **Advanced details**, select the same IAM instance profile as the Linux
   runner. In this guide it grants `AmazonSSMManagedInstanceCore`. Require IMDSv2.
   Leave user data empty so you can install SCT yourself.
- Add your `Project` and `Owner` tags to the instance and its volume. Launch.
- Wait for **Running** and passing status checks. Select the instance and open
    **Connect → Session Manager**. Require that a connection is available. This
    proves the Windows computer has registered with Systems Manager.

Record its ID as **SCT_INSTANCE_ID**, its key-pair name as **SCT_KEY_NAME**, and
its root EBS volume ID. Its instance ID must differ from **RUNNER_ID**.

**Expected:** one additional Windows instance, while the Linux runner remains
running. Both use your runner security group, which still has no inbound rules.

[AWS instance launch procedure](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EC2_GetStarted.html)
and [Windows connection prerequisites](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-rdp.html).

</details>

<details class="instructions" markdown="1">
<summary>CLI alternative: create the same Windows instance from Mac Terminal</summary>

Use your assigned CLI profile. Replace the three `YOUR_...` values using your
worksheet. Set **LAB** to the same prefix used for the rest of your resources.

```bash
export AWS_PROFILE=hydra-lab
export AWS_REGION=us-east-1
export LAB=YOUR_LAB_PREFIX
export RUNNER_ID=YOUR_LINUX_RUNNER_INSTANCE_ID
export RUNNER_SG=YOUR_RUNNER_SECURITY_GROUP_ID
aws sts get-caller-identity
```

Require your assigned account. Read the subnet and instance profile of your
runner, and resolve the current Amazon Windows Server 2022 Base image:

```bash
SCT_SUBNET=$(aws ec2 describe-instances --instance-ids "$RUNNER_ID" --query 'Reservations[0].Instances[0].SubnetId' --output text)
SCT_PROFILE=$(aws ec2 describe-instances --instance-ids "$RUNNER_ID" --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn' --output text)
SCT_AMI=$(aws ssm get-parameter --name /aws/service/ami-windows-latest/Windows_Server-2022-English-Full-Base --query Parameter.Value --output text)
aws ec2 describe-images --image-ids "$SCT_AMI" --query 'Images[0].{Name:Name,Architecture:Architecture,Root:RootDeviceName,Owner:OwnerId}'
```

**Expected:** Amazon's `Windows_Server-2022-English-Full-Base` image, `x86_64`,
and a root device name. Record the AMI ID. A value of `None` for the subnet or
profile means you must correct the runner ID or its configuration first.
[AWS public Windows AMI parameters](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/finding-an-ami-parameter-store.html).

Create a new key pair. `noclobber` prevents overwriting an existing local key.
If the key or AWS name already exists, inspect your previous attempt first.

```bash
umask 077
mkdir -p "$HOME/hydra-lab-notes"
set -o noclobber
export SCT_KEY_NAME="$LAB-sct-key"
aws ec2 create-key-pair --key-name "$SCT_KEY_NAME" --key-type rsa --key-format pem --query KeyMaterial --output text > "$HOME/hydra-lab-notes/$SCT_KEY_NAME.pem"
chmod 600 "$HOME/hydra-lab-notes/$SCT_KEY_NAME.pem"
```

Create the instance. The image supplies the Windows desktop; you install SCT
later. This command creates one new computer and does not install the lab app.

```bash
SCT_ROOT=$(aws ec2 describe-images --image-ids "$SCT_AMI" --query 'Images[0].RootDeviceName' --output text)
SCT_INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "$SCT_AMI" --instance-type t3.large --count 1 \
  --key-name "$SCT_KEY_NAME" \
  --network-interfaces "DeviceIndex=0,SubnetId=$SCT_SUBNET,Groups=$RUNNER_SG,AssociatePublicIpAddress=true,DeleteOnTermination=true" \
  --iam-instance-profile "Arn=$SCT_PROFILE" \
  --metadata-options HttpTokens=required \
  --block-device-mappings "[{\"DeviceName\":\"$SCT_ROOT\",\"Ebs\":{\"VolumeSize\":60,\"VolumeType\":\"gp3\",\"Encrypted\":true,\"DeleteOnTermination\":true}}]" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$LAB-sct},{Key=Project,Value=$LAB}]" "ResourceType=volume,Tags=[{Key=Project,Value=$LAB}]" \
  --query 'Instances[0].InstanceId' --output text)
printf 'SCT_INSTANCE_ID=%s\n' "$SCT_INSTANCE_ID"
```

```bash
aws ec2 wait instance-status-ok --instance-ids "$SCT_INSTANCE_ID"
aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$SCT_INSTANCE_ID" --query 'InstanceInformationList[].{ID:InstanceId,Status:PingStatus,Agent:AgentVersion}'
```

**Expected:** the waiter finishes without an error and SSM shows **Online**.
If SSM has not registered yet, wait and repeat that read-only query. Check the
role, public IP and outbound route if it remains absent. Record the instance,
key-pair and root-volume IDs. Continue with the common connection steps below.

</details>

## 3. Retrieve the Windows password in the AWS Console

- Select **your SCT Windows instance**, choose **Connect**, then **RDP client**.
- Choose **Get password**. If AWS says it is not ready, wait and retry.
- Choose your saved SCT `.pem` file, then **Decrypt password**. This must be the
   key selected for this Windows instance, not a key for another computer.
- Keep the username **Administrator** and the resulting password private.
   You will enter them in Windows App. Do not save them in the shared worksheet.

[AWS Windows password retrieval](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-rdp.html).

<details class="instructions" markdown="1">
<summary>CLI alternative: retrieve and decrypt the password on your Mac</summary>

In Mac Terminal, set the Windows instance ID and the path to its private PEM.
If you created the key in the Console, use the actual downloaded file path.

```bash
export AWS_PROFILE=hydra-lab
export AWS_REGION=us-east-1
export SCT_INSTANCE_ID=YOUR_SCT_WINDOWS_INSTANCE_ID
export SCT_KEY_FILE=YOUR_PRIVATE_PEM_FILE_PATH
umask 077
mkdir -p "$HOME/hydra-lab-notes"
aws ec2 wait password-data-available --instance-id "$SCT_INSTANCE_ID"
aws ec2 get-password-data --instance-id "$SCT_INSTANCE_ID" --query PasswordData --output text > "$HOME/hydra-lab-notes/windows-password.b64"
openssl base64 -d -in "$HOME/hydra-lab-notes/windows-password.b64" -out "$HOME/hydra-lab-notes/windows-password.bin"
openssl pkeyutl -decrypt -inkey "$SCT_KEY_FILE" -pkeyopt rsa_padding_mode:pkcs1 -in "$HOME/hydra-lab-notes/windows-password.bin" -out "$HOME/hydra-lab-notes/windows-password.txt"
```

**Expected:** the waiter and decryption finish without errors. In Finder, open
your home folder, then `hydra-lab-notes`, and open `windows-password.txt` privately.
Use that password with **Administrator**. Do not put this file in the redirected
SCT evidence folder. Delete the temporary password copies when finished.

</details>

## 4. Open the private desktop connection from your Mac

On your Mac, press **Command+Space**, type **Terminal**, and press **Return**.
Replace the instance placeholder with **SCT_INSTANCE_ID**, not the Linux runner.

```bash
aws ssm start-session --profile hydra-lab --region us-east-1 \
  --target YOUR_SCT_WINDOWS_INSTANCE_ID \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["3389"],"localPortNumber":["13389"]}'
```

**Expected:** a session ID and a message waiting for connections. Leave this
Terminal window open. Port **13389** on your Mac now leads to Remote Desktop on
the Windows instance. Your Hydra portal uses a different port, **8080**.

If your CLI login expired, run `aws sso login --profile hydra-lab`, then retry.
If the connection later times out, reopen it and reconnect Windows App.
[AWS port forwarding](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html#sessions-start-port-forwarding).

## 5. Open Windows App on your Mac

- In **Windows App → Devices**, choose **+ → Add PC**.
- Set **PC name** to `127.0.0.1:13389`. Give it a friendly name such as
   `Comcast SCT lab`. Leave the gateway unset; the Terminal session is the path.
- Save it. Edit this PC's settings and open **Folders**. Enable folder
   redirection and add only your Mac's `Documents/Hydra-SCT-evidence` folder.
   Allow writing so SCT reports can be copied back. In **Devices & Audio**,
   allow the clipboard if you want to copy certificate text between computers.
- Save the settings and double-click your new PC. Enter **Administrator** and
   the password you decrypted. Use the local Windows account, not your AWS SSO
   username or Mac password.
- If a certificate prompt appears, inspect its SHA-1 fingerprint. In the AWS
   Console, select the Windows instance and open **Actions → Monitor and
   troubleshoot → Get system log**. Compare it with `RDPCERTIFICATE-THUMBPRINT`.
   Continue only when they match. If the log has not appeared, wait and retry.
- Wait for the Windows desktop. Open **File Explorer → This PC** and find the
   redirected Mac evidence folder under the network locations. Create a small
   text file there and check that it appears in your Mac's Finder folder.

If the desktop fills your Mac screen, choose **Window → Exit Full Screen** from
Windows App's Mac menu. A windowed desktop makes it easier to keep the guide and
AWS Console visible beside it. If Windows asks to make the computer discoverable
on its network, choose **No**; this exercise uses the existing private routes.

**Expected:** a Windows desktop inside an app window on your Mac, plus a working
shared evidence folder. You have not moved Hydra or the database to Windows.

[Microsoft folder and clipboard settings](https://learn.microsoft.com/en-us/windows-app/device-audio-folder-redirection-teams)
and [AWS RDP certificate check](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-rdp.html).

## 6. Install and connect SCT inside the Windows desktop

Open Edge **inside Windows**, then open this guide. Follow the [SCT installation, drivers and trust-store steps](console.md). Install SCT and download its JARs
on Windows. Copy the public trust-store text from the Linux runner as directed.

Use these **direct private connections** for this EC2 desktop:

| SCT setting | Source | Comparison target |
|---|---|---|
| Server name | Native Aurora writer endpoint from your worksheet | Native RDS PostgreSQL endpoint from your worksheet |
| Port | 3306 | 5432 |
| Database/schema | hydra | sct_compare |
| Database user | sct_reader | Your PostgreSQL schema owner |
| TLS | Required, with the RDS trust store | Required, with the RDS trust store |

These are database credentials created in task 2, separate from the Windows
Administrator password. The Windows computer already reaches both databases
through the lab networks. No separate database tunnel or hosts-file change is needed.

To check network access, open **PowerShell inside Windows** and run:

```powershell
Test-NetConnection -ComputerName YOUR_SOURCE_WRITER_ENDPOINT -Port 3306
Test-NetConnection -ComputerName YOUR_TARGET_INSTANCE_ENDPOINT -Port 5432
```

Require **TcpTestSucceeded : True** for both. Then require SCT's own **Test
Connection** to succeed with TLS and the correct database credentials. A TCP
check alone does not prove database login or certificate verification.

Complete the project, assessment, conversion and SQL review in task 3. Copy the
assessment PDF/CSV and reviewed SQL to the redirected Mac evidence folder.
Open them on your Mac to confirm the copy. Keep the SCT project on the Windows
disk while working; copy a final saved version privately if you need to retain it.

## 7. Pause or remove the Windows desktop

Closing Windows App or Terminal only disconnects you. After saving your work,
use **EC2 → your SCT instance → Instance state → Stop instance** between sessions.
Its disk remains and still incurs storage charges. To resume, start that same
instance, wait for checks and SSM, and repeat steps 4-5 with the same instance ID.

When SCT practice and evidence export are finished:

- Open the exported files on your Mac and confirm they are readable.
- In EC2, verify the SCT instance's name and ID against your worksheet.
- Choose **Instance state → Terminate instance** and confirm that instance.
- In **EC2 → Volumes**, check that its recorded root disk was deleted. Record any
   deliberately retained disk or snapshot. Leave the Linux runner running.
- In **EC2 → Key pairs**, delete this SCT-only key pair when no instance uses it.
   Remove its private PEM and temporary password copies from your Mac when no
   longer needed. Keep your reports.

CLI alternative, using the exact IDs and key name from your worksheet:

```bash
aws ec2 terminate-instances --profile hydra-lab --region us-east-1 --instance-ids YOUR_SCT_WINDOWS_INSTANCE_ID
aws ec2 wait instance-terminated --profile hydra-lab --region us-east-1 --instance-ids YOUR_SCT_WINDOWS_INSTANCE_ID
aws ec2 delete-key-pair --profile hydra-lab --region us-east-1 --key-name YOUR_SCT_KEY_NAME
```

Check its recorded EBS volume in the Console after termination. The shared runner
security group, subnet and IAM profile remain in use by the Linux runner.
Remove the saved `Comcast SCT lab` connection from Windows App after teardown.

**Checkpoint:** you created the Windows computer, opened it from your Mac, used
SCT against both private databases, saved your reports on the Mac, and recorded
whether the Windows computer is stopped, running or terminated.
