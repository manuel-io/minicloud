import psycopg2, os, logging, logging.handlers
from flask import Flask
from datetime import datetime
from dateutil import tz

handler = logging.handlers.SysLogHandler(address = '/dev/log')
handler.setFormatter(logging.Formatter('minicloud: [%(levelname)s] %(message)s'))
app = Flask('minicloud')
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

class Config:
    RELEASE = { 'major': 0, 'minor': 0, 'revision': 0 }
    SECRET_KEY = os.urandom(32)
    UTCZONE = tz.UTC
    ZONE = tz.gettz('Europa/Berlin')
    TODAY = datetime.utcnow().replace(tzinfo=UTCZONE).astimezone(ZONE)
    WEEK = TODAY.strftime('%V')

    def __init__():
        pass

    @staticmethod
    def getUnixTimestamp():
        return int(datetime.timestamp(datetime.utcnow().replace(tzinfo=tz.UTC)))

    @staticmethod
    def get_db():
        host = os.environ['MINICLOUD_HOST'] if 'MINICLOUD_HOST' in os.environ else 'localhost'
        dbname = os.environ['MINICLOUD_DBNAME'] if 'MINICLOUD_DBNAME' in os.environ else 'minicloud'
        user = os.environ['MINICLOUD_USR'] if 'MINICLOUD_USR' in os.environ else 'minicloud'
        password = os.environ['MINICLOUD_PWD'] if 'MINICLOUD_PWD' in os.environ else None

        if password:
            return psycopg2.connect(host = host, dbname = dbname, user = user, password = password)
        else:
            return psycopg2.connect(host = host, dbname = dbname, user = user)
