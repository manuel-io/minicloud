import psycopg2, psycopg2.extras
from datetime import datetime
from flask import g, Blueprint, request
from config import app, dbzone, utczone

auths = Blueprint('auths', __name__)

def generate(user_id):
    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              INSERT INTO minicloud_auths (user_id) VALUES (%s) RETURNING token
              """, [user_id])

            data = cursor.fetchone()
            g.db.commit()

        app.logger.info('X-Auth-Token generated')
        return data['token']

    except Exception as e:
        app.logger.error('Generate X-Auth-Token failed: %s' % str(e))
        g.db.rollback()

def revoke(user_id):
    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              DELETE FROM minicloud_auths WHERE user_id = %s
              """, [user_id])

            g.db.commit()
            app.logger.info('X-Auth-Token revoked')

    except Exception as e:
        g.db.rollback()
        app.logger.error('Revoke X-Auth-Token failed: %s' % str(e))

@auths.route("/verify", methods = ["GET"])
def verify():
    token, data = [None, None]

    if 'X-Auth-Token' in request.headers:
        app.logger.info('X-Auth-Token: %s' % request.headers['X-Auth-Token'])
        token = request.headers['X-Auth-Token']

    try:
        if not token:
            raise Exception('not given')

        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT token, created_at FROM minicloud_auths
              WHERE token = %s ORDER BY created_at DESC LIMIT 1
              """, [token])

            data = cursor.fetchone()

        if not data or not data['token'] == token:
            raise Exception('%s invalid' % token)

        # Token is not older then 15min
        created_at = data['created_at'].replace(tzinfo = dbzone).astimezone(utczone).timestamp()
        current_time = datetime.utcnow().replace(tzinfo = utczone).timestamp()

        if (current_time - created_at) > 900:
            raise Exception('%s expired' % token)

        return ('', 201)

    except Exception as e:
        app.logger.error('X-Auth-Token (%s):' % str(e))

    return ('', 401)
