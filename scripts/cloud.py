#!/usr/bin/env python3
"""Cloud practice helpers. Requires explicit sandbox account matching runtime/cloud.json."""
import argparse
import json
import os
from pathlib import Path
import secrets
from urllib.request import urlopen
from lab import env, init, private_write

def engine_versions(response):
    return [v['Version'] for v in response['EngineVersions']]


def main():
    import boto3
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['preflight', 'bootstrap', 'grants', 'endpoints', 'test-endpoints', 'create-task', 'start', 'status', 'stop'])
    p.add_argument('--profile')
    p.add_argument('--region', default='us-east-1')
    p.add_argument('--config', default='runtime/cloud.json')
    a = p.parse_args()
    session = boto3.Session(profile_name=a.profile, region_name=a.region)
    account = session.client('sts').get_caller_identity()['Account']
    if a.action == 'preflight':
        rds = session.client('rds')
        print('Authenticated AWS account:', account)
        for engine, major in [('aurora-mysql', '8.0.mysql_aurora.3.'), ('aurora-postgresql', '17.')]:
            versions = []
            for page in rds.get_paginator('describe_db_engine_versions').paginate(Engine=engine):
                versions += [v['EngineVersion'] for v in page['DBEngineVersions'] if v['EngineVersion'].startswith(major)]
            print(engine, json.dumps(versions))
        print('DMS:', engine_versions(session.client('dms').describe_engine_versions()))
        for role in ('dms-vpc-role', 'dms-cloudwatch-logs-role'):
            try:
                session.client('iam').get_role(RoleName=role)
                print(role, 'exists')
            except session.client('iam').exceptions.NoSuchEntityException:
                print(role, 'absent')
        return
    cfg = json.loads(Path(a.config).read_text())
    if account != cfg['account_id'] or a.region != cfg['region']:
        raise SystemExit('Account/region mismatch: refusing to operate on this environment.')
    sm = session.client('secretsmanager')
    dms = session.client('dms')
    state_path = Path('runtime/dms.json')
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if a.action in ('bootstrap', 'grants'):
        import pymysql
        import psycopg
        from psycopg import sql
        init()
        values = env()
        cert = Path('runtime/certs/global-bundle.pem')
        cert.parent.mkdir(parents=True, exist_ok=True)
        if not cert.exists():
            cert.write_bytes(urlopen('https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem', timeout=30).read())
        # Public CA material is mounted into Hydra, which runs as a different UID.
        cert.parent.chmod(0o755)
        cert.chmod(0o644)
        admins = {name: json.loads(sm.get_secret_value(SecretId=cfg[name]['master_secret_arn'])['SecretString']) for name in ('source', 'target')}
        source = pymysql.connect(host=cfg['source']['host'], user=admins['source']['username'], password=admins['source']['password'], database='hydra', ssl={'ca': str(cert.resolve()), 'check_hostname': True}, autocommit=True)
        target = psycopg.connect(host=cfg['target']['host'], user=admins['target']['username'], password=admins['target']['password'], dbname='hydra', sslmode='verify-full', sslrootcert=str(cert.resolve()), autocommit=True)
        if a.action == 'bootstrap':
            values.setdefault('SCT_PASSWORD', secrets.token_hex(24))
            with source.cursor() as c:
                c.execute("CREATE USER IF NOT EXISTS 'hydra'@'%%' IDENTIFIED BY %s", (values['MYSQL_PASSWORD'],))
                c.execute("ALTER USER 'hydra'@'%%' IDENTIFIED BY %s", (values['MYSQL_PASSWORD'],))
                c.execute("GRANT ALL ON hydra.* TO 'hydra'@'%'")
                c.execute("CALL mysql.rds_set_configuration('binlog retention hours', 72)")
                c.execute("CREATE USER IF NOT EXISTS 'sct_reader'@'%%' IDENTIFIED BY %s", (values['SCT_PASSWORD'],))
                c.execute("ALTER USER 'sct_reader'@'%%' IDENTIFIED BY %s", (values['SCT_PASSWORD'],))
                c.execute("GRANT SELECT, SHOW VIEW ON *.* TO 'sct_reader'@'%'")
            with target.cursor() as c:
                c.execute("SELECT 1 FROM pg_roles WHERE rolname='hydra'")
                if not c.fetchone():
                    c.execute('CREATE ROLE hydra LOGIN')
                c.execute(sql.SQL('ALTER ROLE hydra PASSWORD {}').format(sql.Literal(values['POSTGRES_PASSWORD'])))
                c.execute(sql.SQL('GRANT hydra TO {}').format(sql.Identifier(admins['target']['username'])))
                c.execute('GRANT CONNECT ON DATABASE hydra TO hydra')
                c.execute('ALTER SCHEMA public OWNER TO hydra')
                c.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
                c.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
                c.execute("SELECT 1 FROM pg_database WHERE datname='sct_compare'")
                if not c.fetchone():
                    c.execute('CREATE DATABASE sct_compare OWNER hydra')
            values.update(MYSQL_HOST=cfg['source']['host'], POSTGRES_HOST=cfg['target']['host'], COMPOSE_FILE='compose.cloud.yaml')
            private_write(Path('.env'), ''.join(f'{k}={v}\n' for k, v in values.items()))
            config = {'source': {'host': cfg['source']['host'], 'port': 3306, 'user': 'hydra', 'password': values['MYSQL_PASSWORD'], 'database': 'hydra', 'ssl': {'ca': str(cert.resolve()), 'check_hostname': True}}, 'target': {'host': cfg['target']['host'], 'port': 5432, 'user': 'hydra', 'password': values['POSTGRES_PASSWORD'], 'dbname': 'hydra', 'sslmode': 'verify-full', 'sslrootcert': str(cert.resolve())}}
            private_write(Path('runtime/databases.json'), json.dumps(config, indent=2))
            print('Hydra schema-owner accounts created. Cloud Compose selected. Run lab.py up before grants.')
        else:
            passwords = {n: secrets.token_hex(24) for n in ('source', 'target')}
            with source.cursor() as c:
                c.execute("CREATE USER IF NOT EXISTS 'dms_repl'@'%%' IDENTIFIED BY %s", (passwords['source'],))
                c.execute("ALTER USER 'dms_repl'@'%%' IDENTIFIED BY %s", (passwords['source'],))
                c.execute("GRANT SELECT ON hydra.* TO 'dms_repl'@'%'")
                c.execute("GRANT REPLICATION CLIENT, REPLICATION SLAVE ON *.* TO 'dms_repl'@'%'")
            with target.cursor() as c:
                c.execute("SELECT 1 FROM pg_roles WHERE rolname='dms_apply'")
                if not c.fetchone():
                    c.execute('CREATE ROLE dms_apply LOGIN')
                c.execute(sql.SQL('ALTER ROLE dms_apply PASSWORD {}').format(sql.Literal(passwords['target'])))
                c.execute('GRANT CONNECT ON DATABASE hydra TO dms_apply')
                c.execute('GRANT USAGE ON SCHEMA public TO dms_apply')
                c.execute('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO dms_apply')
                c.execute('CREATE SCHEMA IF NOT EXISTS awsdms_control AUTHORIZATION dms_apply')
                c.execute('GRANT USAGE,CREATE ON SCHEMA awsdms_control TO dms_apply')
                c.execute('GRANT SET ON PARAMETER session_replication_role TO dms_apply')
            for n in ('source', 'target'):
                sm.put_secret_value(SecretId=cfg[n]['dms_secret_arn'], SecretString=json.dumps({'username': 'dms_repl' if n == 'source' else 'dms_apply', 'password': passwords[n], 'host': cfg[n]['host'], 'port': cfg[n]['port']}))
            print('DMS users and endpoint secrets created. Re-running rotates their passwords; do not run during a task.')
        source.close()
        target.close()
    elif a.action == 'endpoints':
        cert = Path('runtime/certs/' + a.region + '-bundle.pem')
        if not cert.exists():
            cert.parent.mkdir(parents=True, exist_ok=True)
            cert.write_bytes(urlopen(f'https://truststore.pki.rds.amazonaws.com/{a.region}/{a.region}-bundle.pem', timeout=30).read())
        cert_id = cfg['name'] + '-rds-ca'
        existing = dms.describe_certificates(Filters=[{'Name': 'certificate-id', 'Values': [cert_id]}])['Certificates']
        certificate_arn = existing[0]['CertificateArn'] if existing else dms.import_certificate(CertificateIdentifier=cert_id, CertificatePem=cert.read_text())['Certificate']['CertificateArn']
        for n in ('source', 'target'):
            endpoint_id = cfg['name'] + '-' + n
            existing = dms.describe_endpoints(Filters=[{'Name': 'endpoint-id', 'Values': [endpoint_id]}])['Endpoints']
            if existing:
                state[n] = existing[0]['EndpointArn']
                continue
            settings = {'SecretsManagerAccessRoleArn': cfg['dms_secrets_role_arn'], 'SecretsManagerSecretId': cfg[n]['dms_secret_arn']}
            if n == 'target':
                settings['AfterConnectScript'] = 'SET session_replication_role=replica'
            request = {'EndpointIdentifier': endpoint_id, 'EndpointType': n, 'EngineName': 'aurora' if n == 'source' else 'aurora-postgresql', 'SslMode': 'verify-full', 'CertificateArn': certificate_arn, 'Tags': [{'Key': 'Project', 'Value': cfg['name']}]}
            request['MySQLSettings' if n == 'source' else 'PostgreSQLSettings'] = settings
            if n == 'target':
                request['DatabaseName'] = 'hydra'
            state[n] = dms.create_endpoint(**request)['Endpoint']['EndpointArn']
        private_write(state_path, json.dumps(state, indent=2))
        print('Endpoints created. Test both before creating a task.')
    elif a.action == 'test-endpoints':
        for n in ('source', 'target'):
            dms.test_connection(ReplicationInstanceArn=cfg['dms_instance_arn'], EndpointArn=state[n])
        print('Connection tests requested; inspect status until both are successful.')
    elif a.action == 'create-task':
        preflight = json.loads(Path('evidence/lob-check.json').read_text())
        if not preflight.get('pass'):
            raise SystemExit('LOB preflight must pass first.')
        response = dms.create_replication_task(ReplicationTaskIdentifier=cfg['name'], SourceEndpointArn=state['source'], TargetEndpointArn=state['target'], ReplicationInstanceArn=cfg['dms_instance_arn'], MigrationType='full-load-and-cdc', TableMappings=Path('runtime/table-mappings.json').read_text(), ReplicationTaskSettings=Path('migration/task-settings.json').read_text(), Tags=[{'Key': 'Project', 'Value': cfg['name']}])
        state['task'] = response['ReplicationTask']['ReplicationTaskArn']
        private_write(state_path, json.dumps(state, indent=2))
        print('Task created but not started. Inspect configuration and target emptiness first.')
    elif a.action == 'start':
        dms.start_replication_task(ReplicationTaskArn=state['task'], StartReplicationTaskType='start-replication')
        print('Initial full load and CDC requested. For recovery, choose resume-processing explicitly in AWS.')
    elif a.action == 'stop':
        dms.stop_replication_task(ReplicationTaskArn=state['task'])
        print('Task stop requested; verify stopped state before target writes.')
    else:
        result = {'connections': dms.describe_connections(Filters=[{'Name': 'replication-instance-arn', 'Values': [cfg['dms_instance_arn']]}])['Connections']}
        if 'task' in state:
            result['task'] = dms.describe_replication_tasks(Filters=[{'Name': 'replication-task-arn', 'Values': [state['task']]}], WithoutSettings=True)['ReplicationTasks']
            tables = []
            marker = None
            while True:
                kwargs = {'ReplicationTaskArn': state['task'], 'MaxRecords': 100}
                if marker:
                    kwargs['Marker'] = marker
                page = dms.describe_table_statistics(**kwargs)
                tables += page['TableStatistics']
                marker = page.get('Marker')
                if not marker:
                    break
            result['tables'] = tables
        Path('evidence').mkdir(exist_ok=True)
        Path('evidence/dms-status.json').write_text(json.dumps(result, indent=2, default=str))
        print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
