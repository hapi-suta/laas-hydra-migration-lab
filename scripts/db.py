"""Shared database connections and cross-engine canonicalization."""
import base64
import datetime
import decimal
import json
from pathlib import Path
import uuid


def connections(path='runtime/databases.json'):
    import pymysql
    import psycopg
    conf = json.loads(Path(path).read_text())
    return pymysql.connect(**conf['source'], autocommit=True), psycopg.connect(**conf['target'], autocommit=True)


def ident(name, engine='mysql'):
    quote = '`' if engine == 'mysql' else '"'
    return quote + name.replace(quote, quote + quote) + quote


def canonical(value, target_type=''):
    if value is None:
        return None
    if target_type == 'boolean':
        if value in (True, 1, '1', b'1', 'true', 't'):
            return True
        if value in (False, 0, '0', b'0', 'false', 'f'):
            return False
        raise ValueError('Invalid boolean representation')
    if target_type in ('json', 'jsonb'):
        return json.loads(value) if isinstance(value, (str, bytes)) else value
    if isinstance(value, (bytes, bytearray, memoryview)):
        if target_type == 'uuid' and len(value) == 16:
            return str(uuid.UUID(bytes=bytes(value)))
        if target_type in ('text', 'character varying', 'uuid'):
            return bytes(value).decode()
        return {'base64': base64.b64encode(value).decode()}
    if isinstance(value, datetime.datetime):
        if value.tzinfo:
            value = value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return value.isoformat(timespec='microseconds')
    if isinstance(value, (datetime.date, uuid.UUID)):
        return str(value)
    if isinstance(value, decimal.Decimal):
        return str(value.normalize())
    return value


def schema(source, target):
    with source.cursor() as c:
        c.execute("SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema=DATABASE() ORDER BY table_name,ordinal_position")
        src = {}
        for table, col, typ in c:
            src.setdefault(table, {})[col] = typ
    with target.cursor() as c:
        c.execute("SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position")
        dst = {}
        for table, col, typ in c:
            dst.setdefault(table, {})[col] = typ
    return src, dst
