# Install your workstation tools

Choose the instructions for your workstation. These tools let you authenticate
and open SSM tunnels. AWS resource creation can use CloudShell, which already
includes AWS CLI. SCT desktop installation is in [Module 04](04-sct/console.md).

## 1. Install AWS CLI v2

### Windows

1. Open [AWS's Windows installer instructions](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
2. Download the linked 64-bit MSI, open it and complete the setup wizard.
3. Open a new PowerShell window and run `aws --version`.

CLI alternative in an elevated PowerShell window:

```powershell
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

### macOS

Download the PKG from the same AWS installation page and open the installer.
Complete its steps, then open a new terminal. CLI alternative in Terminal:

```bash
curl -fL https://awscli.amazonaws.com/AWSCLIV2.pkg -o AWSCLIV2.pkg
```

```bash
sudo installer -pkg AWSCLIV2.pkg -target /
```

### Linux x86_64

Install unzip using your distribution package manager if it is missing. In your
own terminal:

```bash
curl -fL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip
```

```bash
unzip awscliv2.zip
```

```bash
sudo ./aws/install
```

For ARM64 Linux, select AWS's ARM installer on the installation page instead.
Follow AWS's linked signature-verification procedure if your workstation policy
requires it. Do not install a package for the wrong architecture.

On every OS, verify:

```bash
aws --version
```

Expected: **aws-cli/2**. If an older binary appears, inspect your PATH and open a
new terminal before configuring credentials.

## 2. Install the Session Manager plugin

Open [AWS's plugin installation instructions](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)
and select your OS.

- **Windows:** download the linked `SessionManagerPluginSetup.exe`, run it, accept
  the installation directory and finish. Open a new PowerShell window.
- **macOS:** use the signed installer linked in AWS's macOS instructions. Choose
  the correct processor architecture, open the package and complete installation.
- **Ubuntu/Debian:** download the architecture-specific `.deb` from the AWS page,
  then run `sudo dpkg -i session-manager-plugin.deb` in its download directory.
- **Amazon Linux/RHEL:** download the architecture-specific `.rpm` from the AWS
  page, then run `sudo yum install -y session-manager-plugin.rpm` in that directory.

For **Apple silicon macOS**, the signed-installer CLI path is:

```bash
curl -fL https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac_arm64/session-manager-plugin.pkg -o session-manager-plugin.pkg
```

For an **Intel Mac**, use this download instead:

```bash
curl -fL https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/session-manager-plugin.pkg -o session-manager-plugin.pkg
```

Then install the downloaded package:

```bash
sudo installer -pkg session-manager-plugin.pkg -target /
```

Ensure the executable is on PATH. Inspect `ls -l /usr/local/bin/session-manager-plugin`.
If the link is absent, create the directory and link:

```bash
sudo mkdir -p /usr/local/bin
```

```bash
sudo ln -s /usr/local/sessionmanagerplugin/bin/session-manager-plugin /usr/local/bin/session-manager-plugin
```

Do not overwrite an existing working link. These are the
[AWS signed macOS installation steps](https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-macos-overview.html).

In a new terminal, run:

```bash
session-manager-plugin
```

Expected: a message that the plugin was installed successfully. If not found,
check AWS's documented installation path and PATH guidance for your OS. The
plugin is required on the workstation that opens the tunnel, not just the runner.

## 3. Authenticate and verify the account

Return to [Before you begin](start.md#1-sign-in-and-identify-the-account) for SSO
profile setup, browser authentication and STS identity verification. Keep the
same account and us-east-1 region for the whole exercise. Do not place long-lived
access keys in the downloaded project.

## 4. Verify the tunnel prerequisites

After creating your runner, use the exact [portal tunnel command](03-data/build.md#6-create-actual-oauth-state-through-the-browser).
The runner must be SSM Online. A successful session should print **Waiting for
connections**. Keep it open and browse to **http://localhost:8080**.
If the port is occupied, stop your own conflicting local service before retrying;
changing only the browser port would break the configured OAuth callback URL.
