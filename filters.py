import psycopg2, psycopg2.extras
from functools import reduce
from flask import g
from config import app

def get_directors(ref):
    data, directors = [ None, [] ]

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT array_agg(DISTINCT director ORDER BY director) AS directors
              FROM minicloud_multimedia WHERE type = %s
              """, [ref])

            data = cursor.fetchone()

        if data:
            if type(data['directors']) is list:
                directors = data['directors']

    except Exception as e:
        app.logger.error('Filters get_directors failed: %s' % str(e))

    return directors

def get_actors(ref):
    data, actors = [ None, [] ]

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT count(actor) AS count, actor
              FROM minicloud_multimedia, unnest(actors) AS actor
              WHERE length(actor) > 0 AND type = %s
              GROUP BY actor ORDER BY count DESC LIMIT 50
              """, [ref])

            data = cursor.fetchall()

        if data:
            actors = reduce(lambda acc, item: acc + [item['actor']], data, [])

    except Exception as e:
        app.logger.error('Filters get_actors failed: %s' % str(e))

    return actors
