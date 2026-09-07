#!/usr/bin/env bash
# Run as ec2-user on the Amazon Linux 2023 practice runner.
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
sudo dnf install -y java-17-amazon-corretto-headless
mkdir -p runtime/sct evidence/sct
curl -fLsS --retry 2 --max-time 300 \
  https://s3.amazonaws.com/publicsctdownload/jars/AWSSchemaConversionToolBatch.jar \
  -o runtime/sct/AWSSchemaConversionToolBatch.jar
curl -fLsS --retry 2 --max-time 120 \
  https://repo.maven.apache.org/maven2/com/mysql/mysql-connector-j/26.7.0/mysql-connector-j-26.7.0.jar \
  -o runtime/sct/mysql.jar
curl -fLsS --retry 2 --max-time 120 \
  https://jdbc.postgresql.org/download/postgresql-42.7.13.jar \
  -o runtime/sct/postgresql.jar
sha256sum runtime/sct/*.jar > evidence/sct-download.sha256
python3 - <<'PY'
from pathlib import Path
import zipfile
p=Path('runtime/sct/AWSSchemaConversionToolBatch.jar')
with zipfile.ZipFile(p) as archive:
    manifest=archive.read('META-INF/MANIFEST.MF').decode()
    if archive.testzip() is not None:
        raise SystemExit('SCT archive integrity check failed')
Path('evidence/sct-version.txt').write_text(manifest)
print(manifest)
PY
printf 'Installed SCT and JDBC drivers; hashes and version recorded under evidence.\n'
