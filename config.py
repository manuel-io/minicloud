import psycopg2, os, logging, logging.handlers
from flask import Flask
from datetime import datetime
from dateutil import tz

app = Flask('minicloud')
handler = logging.handlers.SysLogHandler(address = '/dev/log')
handler.setFormatter(logging.Formatter('minicloud: [%(levelname)s] %(message)s'))
app = Flask(__name__)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

utczone = tz.gettz('UTC')
dbzone = tz.gettz('UTC')
zone = tz.gettz('Europa/Berlin')
today = datetime.utcnow().replace(tzinfo = utczone).astimezone(zone)

class Config:
    VERSION = 0.9
    SECRET_KEY = os.urandom(32)

    def __init__():
        pass

    @staticmethod
    def getUnixTimestamp():
        return int(datetime.timestamp(datetime.utcnow().replace(tzinfo = tz.UTC)))


def get_db():
    host = os.environ['MINICLOUD_HOST'] if 'MINICLOUD_HOST' in os.environ else 'localhost'
    dbname = os.environ['MINICLOUD_DBNAME'] if 'MINICLOUD_DBNAME' in os.environ else 'minicloud'
    user = os.environ['MINICLOUD_USR'] if 'MINICLOUD_USR' in os.environ else 'minicloud'
    password = os.environ['MINICLOUD_PWD'] if 'MINICLOUD_PWD' in os.environ else None 

    if password:
        return psycopg2.connect(host = host, dbname = dbname, user = user, password = password)
    else:
        return psycopg2.connect(host = host, dbname = dbname, user = user)

MIME_SUFFIX = { 'text/plain': 'txt'
              , 'text/x-python': 'rb'
              , 'application/x-ruby': 'rb'
              , 'text/x-haskell': 'hs'
              , 'text/x-csrc': 'c'
              , 'application/x-javascript': 'js'
              , 'application/x-shellscript': 'sh'
              , 'application/octet-stream': 'part'
              , 'text/html': 'html'
              , 'text/css': 'css'
              , 'text/markdown': 'md'
              , 'font/ttf': 'ttf'
              , 'font/otf': 'otf'
              , 'application/pdf': 'pdf'
              , 'application/x-tar': 'tar'
              , 'application/x-xz': 'xz'
              , 'application/zip': 'zip'
              , 'application/gzip': 'gzip'
              , 'image/jpeg': 'jpg'
              , 'image/png': 'png'
              , 'image/svg+xml': 'svg'
              , 'image/x-icon': 'ico'
              , 'image/webp': 'webp'
              , 'audio/mpeg': 'mp3'
              , 'audio/ogg': 'oga'
              , 'audio/x-wav': 'wav'
              , 'audio/x-mpegurl': 'm3u'
              , 'audio/opus': 'opus'
              , 'audio/webm': 'webm'
              , 'video/avi': 'avi'
              , 'video/mp4': 'mp4'
              , 'video/ogg': 'ogv'
              , 'video/webm': 'webm'
              }

config = { "general": { "utczone": utczone
                      , "dbzone": dbzone
                      , "zone": zone
                      , "today": today
                      , "week": today.strftime('%V')
                      }
         , "categories": { "default": "Default" }
         , "tasks": { "states": [ "pending"
                                , "processing"
                                , "completed"
                                , "deleted"
                                ]
                    }
         , "ftypes": { "plain":    [ "text/plain"
                                   , "text/plain"
                                   ]
                     , "code":     [ "text/x-python"
                                   , "text/x-ruby"
                                   , "text/x-haskell"
                                   , "text/x-csrc"
                                   , "application/x-ruby"
                                   , "application/x-javascript"
                                   , "application/x-shellscript"
                                   , "application/octet-stream"
                                   ]
                     , "markup":   [ "text/html"
                                   , "text/css"
                                   , "text/markdown"
                                   ]
                     , "font":     [ "font/ttf"
                                   , "font/otf"
                                   ]
                     , "document": [ "application/pdf"
                                   , "application/pdf"
                                   ]
                     , "archive":  [ "application/x-tar"
                                   , "application/x-xz"
                                   , "application/zip"
                                   , "application/gzip"
                                   ]
                     , "image":    [ "image/jpeg"
                                   , "image/png"
                                   , "image/svg+xml"
                                   , "image/webp"
                                   ]
                     , "icon":     [ "image/x-icon"
                                   ]
                     , "audio":    [ "audio/mpeg"
                                   , "audio/ogg"
                                   , "audio/x-wav"
                                   , "audio/x-mpegurl"
                                   , "audio/opus"
                                   ]
                     , "video":    [ "video/avi"
                                   , "video/mp4"
                                   , "video/ogg"
                                   , "video/webm"
                                   ]
                     }
         }
