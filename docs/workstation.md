# Install tools on your Mac

**Where:** your own Mac. Start before connecting to an EC2 computer.
You need AWS CLI, the Session Manager plugin, and Windows App. The AWS CLI and
plugin open private connections. Windows App displays your SCT computer later.
Hydra, Docker and the databases run in AWS.

## 1. Check whether your Mac uses Apple silicon or Intel

Choose **Apple menu → About This Mac**. Record the macOS version and look for
**Chip** or **Processor**. An Apple M-series chip means Apple silicon. A processor
label containing Intel means an Intel Mac. You will choose the matching Session
Manager download in step 3.

## 2. Install AWS CLI v2

### Installer route

- In Safari or Chrome, open [AWS's CLI installation page](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
- Expand **macOS** and follow its graphical installer link to download
   `AWSCLIV2.pkg`.
- Open **Finder → Downloads** and double-click the package. Continue through the
   installer, choose **Install**, and approve it using your Mac's login when asked.
- Open a new Terminal: press **Command+Space**, type **Terminal**, then press
   **Return**. Run the check below.

```bash
aws --version
```

**Expected:** the first part is `aws-cli/2`. The exact version numbers can differ.
If the command is not found, close Terminal, open a new window and retry. Follow
AWS's PATH troubleshooting if it still fails.

### Terminal alternative

Use this instead of the graphical installation, not after it:

```bash
curl -fL https://awscli.amazonaws.com/AWSCLIV2.pkg -o AWSCLIV2.pkg
sudo installer -pkg AWSCLIV2.pkg -target /
aws --version
```

When `sudo` asks for your Mac password, typing it does not display characters.
Press Return after entering it. This is your Mac login, not an AWS password.

## 3. Install the Session Manager plugin

### Installer route

- Open [AWS's signed macOS plugin instructions](https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-macos-overview.html).
- Choose the signed package for **Apple silicon** or **Intel**, matching step 1.
- Open the downloaded `.pkg` from Finder and complete the installer.
- Open a new Terminal window and run:

```bash
session-manager-plugin
```

**Expected:** a message saying the plugin was installed successfully. It is a
connection helper; it does not open a desktop or the Hydra app by itself.

### Terminal alternative

For **Apple silicon**, download:

```bash
curl -fL https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac_arm64/session-manager-plugin.pkg -o session-manager-plugin.pkg
```

For **Intel**, use this download instead:

```bash
curl -fL https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/session-manager-plugin.pkg -o session-manager-plugin.pkg
```

Then install the package you selected:

```bash
sudo installer -pkg session-manager-plugin.pkg -target /
session-manager-plugin
```

If the command is not found, inspect the link in Terminal:

```bash
ls -l /usr/local/bin/session-manager-plugin
```

If that link is absent, follow AWS's installation path and create the link:

```bash
sudo mkdir -p /usr/local/bin
sudo ln -s /usr/local/sessionmanagerplugin/bin/session-manager-plugin /usr/local/bin/session-manager-plugin
session-manager-plugin
```

A working link must not be replaced. The plugin must be installed on this Mac,
which opens the private connections.

## 4. Install Windows App for the SCT desktop

- Open the **Mac App Store**. Search for **Windows App** and confirm the publisher
   is Microsoft. Install it.
- Open Windows App. Finish or skip its introductory tour.
- Leave it ready. You have no SCT computer to connect to yet. In task 3 you will
   create Windows EC2 and add it using **Devices → + → Add PC**.

[Microsoft's Mac connection instructions](https://learn.microsoft.com/en-us/windows-app/get-started-connect-devices-desktops-apps).

## 5. Sign in to AWS CLI on your Mac

Return to [Mac sign-in, step 3](start.md#3-sign-in-on-your-workstation-for-the-private-app-connection).
Configure your assigned login and verify the account ID. A signed-in AWS browser
tab does not automatically sign in your Mac Terminal.

**Ready to continue:** `aws --version` shows version 2, the Session Manager plugin
check succeeds, Windows App opens, and your CLI account matches the assigned AWS
Console account. Continue with the worksheet and task 1.

## Later: understand the two private connections

| Connection opened in Mac Terminal | What you open on the Mac | When it becomes useful |
|---|---|---|
| Port 8080 to the Linux runner | Browser → http://localhost:8080 | Task 2, after starting Hydra and the portal |
| Port 13389 to the Windows SCT instance | Windows App → 127.0.0.1:13389 | Task 3, after creating Windows EC2 |

Keep each connection's Terminal window open while using it. A connection ending
or timing out does not delete or stop the EC2 computer. The exact commands and
expected messages appear in their tasks.
