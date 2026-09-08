#!/usr/bin/env python3
"""Run a private SCT connection inspection or schema assessment against the lab."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
from urllib.request import urlopen
from lab import env, private_write

ROOT = Path(__file__).resolve().parents[1]

def command(operation, **parameters):
    for value in parameters.values():
        if "'" in str(value) or "\n" in str(value):
            raise ValueError('SCT parameter contains unsupported quote/newline')
    return operation + ''.join(f" -{key}: '{value}'" for key, value in parameters.items()) + '\n/\n'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['inspect','assess'])
    p.add_argument('--java', default='java')
    a=p.parse_args()
    os.chdir(ROOT)
    cfg=json.loads(Path('runtime/cloud.json').read_text())
    values=env()
    base=ROOT/'runtime/sct'
    out=ROOT/'evidence/sct'
    base.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    java=shutil.which(a.java) or a.java
    keytool=str(Path(java).resolve().parent/'keytool')
    trust=base/'rds-trust.jks'
    trustpass=values.get('SCT_TRUST_PASSWORD')
    if not trustpass:
        trustpass='Sct9!'+secrets.token_hex(20)
        values['SCT_TRUST_PASSWORD']=trustpass
        private_write(ROOT/'.env', ''.join(f'{k}={v}\n' for k,v in values.items()))
    if not trust.exists():
        region=cfg['region']
        pem=urlopen(f'https://truststore.pki.rds.amazonaws.com/{region}/{region}-bundle.pem',timeout=30).read().decode()
        for i,cert in enumerate(re.findall(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----',pem,re.S)):
            path=base/f'ca-{i}.pem'
            path.write_text(cert+'\n')
            childenv=dict(os.environ,SCT_TRUST_PASSWORD=trustpass)
            subprocess.run([keytool,'-importcert','-noprompt','-alias',f'rds-{i}','-file',str(path),'-keystore',str(trust),'-storetype','JKS','-storepass:env','SCT_TRUST_PASSWORD'],env=childenv,check=True,capture_output=True)
    script=command('SetGlobalSettings', settings=json.dumps({'mysql_driver_file':str(base/'mysql.jar'),'postgresql_driver_file':str(base/'postgresql.jar')}),save='true')
    script+=command('CreateProject',name='hydra_'+a.action,directory=str(base))
    script+=command('LoadTrustStore',name='RDS',password=trustpass,file=str(trust))
    tls={'useSSL':'true','requireSSL':'true','verifyServerCertificate':'true','trustServerCertificate':'false','trustStoreAlias':'RDS'}
    script+=command('AddSource',name='MYSQL',vendor='MYSQL',host=cfg['source']['host'],port='3306',user='sct_reader',password=values['SCT_PASSWORD'],**tls)
    script+=command('AddTarget',name='POSTGRESQL',vendor='POSTGRESQL',host=cfg['target']['host'],port='5432',database='sct_compare',user='hydra',password=values['POSTGRES_PASSWORD'],**tls)
    script+=command('AddServerMapping',sourceTreePath='Servers.MYSQL',targetTreePath='Servers.POSTGRESQL')
    script+=command('PrintSourceTreeNodeChildren',treePath='Servers.MYSQL')
    if a.action=='assess':
        source='Servers.MYSQL.Schemas.hydra'
        script+=command('CreateReport',treePath=source)
        script+=command('Convert',treePath=source)
        script+=command('SaveTargetSQL',treePath='Servers.POSTGRESQL.Schemas.hydra',file=str(out/'converted.sql'))
        script+=command('SaveReportPDF',file=str(out/'assessment.pdf'))
        script+=command('SaveReportCSV',directory=str(out))
    script+=command('SaveProject')
    path=base/(a.action+'.scts')
    private_write(path,script)
    log=out/(a.action+'.log')
    # SCT logs can echo command parameters. Keep the raw log private and redact
    # both successful output and failure output before displaying it.
    private_write(log,'')
    with log.open('w') as f:
        r=subprocess.run([java,'--add-opens=java.base/jdk.internal.loader=ALL-UNNAMED','-Xmx2g','-Djdk.jar.maxSignatureFileSize=128000000','-jar',str(base/'AWSSchemaConversionToolBatch.jar'),'-type','scts','-script',str(path)],stdout=f,stderr=subprocess.STDOUT,timeout=900)
    content=log.read_text(errors='replace')
    for key,value in values.items():
        if ('PASSWORD' in key or 'SECRET' in key) and value:
            content=content.replace(value,'[REDACTED]')
    lines=[line for line in content.splitlines() if len(line)<1800 and any(word in line for word in ('ERROR','failed','finished','Schemas','Databases','Tables','SSL'))]
    print('\n'.join(lines[-55:]))
    failed=r.returncode!=0 or ' ERROR ' in content
    if a.action=='assess':
        failed |= not all((out/f).exists() and (out/f).stat().st_size>0 for f in ('assessment.pdf','converted.sql'))
    if failed:
        raise SystemExit('SCT did not complete; inspect the private log. No application target schema was modified.')
    if a.action=='assess':
        # SCT build 677 cannot export DROP DDL for a MySQL CHECK constraint.
        # Capture the native CREATE definitions directly, without drop statements.
        import pymysql
        from db import ident
        source_config=json.loads(Path('runtime/databases.json').read_text())['source']
        source_config.update(user='sct_reader',password=values['SCT_PASSWORD'])
        con=pymysql.connect(**source_config)
        ddl=[]
        with con.cursor() as cursor:
            cursor.execute("SHOW FULL TABLES WHERE Table_type='BASE TABLE'")
            names=[row[0] for row in cursor.fetchall()]
            for table in names:
                cursor.execute('SHOW CREATE TABLE '+ident(table))
                ddl.append(cursor.fetchone()[1]+';')
        con.close()
        private_write(out/'source.sql','-- Native SHOW CREATE TABLE export; schema only.\n\n'+'\n\n'.join(ddl))
    print('SCT '+a.action+' completed; private evidence: '+str(out))

if __name__=='__main__': main()
