import psycopg2, psycopg2.extras
from flask import g, Blueprint, request
from config import app

auths = Blueprint('auths', __name__)

def generate(user_id):
    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              INSERT INTO minicloud_auths (user_id)
              VALUES (%s) RETURNING token
              """ % user_id)

            data = cursor.fetchone()
            g.db.commit()

        return data['token']

    except Exception as e:
        app.logger.error('Generate token failed: %s' % str(e))
        g.db.rollback()

@auths.route("/verify", methods = ["GET"])
def verify():
    if 'X-Auth-Token' in request.headers:
        app.logger.info('X-Auth-Token: %s' % request.headers['X-Auth-Token'])
        token = request.headers['X-Auth-Token']

    try:
        if not token:
            raise Exception('not given')

        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT token FROM minicloud_auths
              WHERE token = %s RETURNING token
              """, (token))

            data = cursor.fetchone()

        if not data['token'] == token:
            raise Exception('%s invalid' % token)

        else:
            return ('', 201)

    except Exception as e:
        app.logger.error('Token: %s' % str(e))

    return ('', 401)
