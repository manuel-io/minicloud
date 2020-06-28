import psycopg2, psycopg2.extras, uuid, re, io, glob, os.path, requests
import auths
from datetime import datetime
from dateutil import parser
from flask import Blueprint, g, request, Response, render_template, url_for, redirect, jsonify, make_response, flash, send_file, send_from_directory, abort
from users import login_required, admin_required, current_user
from config import app, config
from pathlib import Path
from minidlna import MiniDLNA
from helpers import get_categories

multimedia = Blueprint('multimedia', __name__)
base = Path('/var/minicloud/multimedia')
minidlna = os.environ['MINICLOUD_DLNA'] if 'MINICLOUD_DLNA' in os.environ else 'http://127.0.0.1:8200'
minidlna_verify = False if 'MINICLOUD_DLNA_NOVERIFY' in os.environ else True
minidlna_proxy_host = os.environ['MINICLOUD_DLNA_PROXY_HOST'] if 'MINICLOUD_DLNA_PROXY_HOST' in os.environ else None
minidlna_proxy_port = os.environ['MINICLOUD_DLNA_PROXY_PORT'] if 'MINICLOUD_DLNA_PROXY_PORT' in os.environ else None

def find_local_files():
    return list(map(lambda path: str(path.relative_to(base)), list(base.rglob('*.*'))))

def find_minidlna_files(user_id):
    auth = auths.generate(user_id)
    print('auth', auth)
    return MiniDLNA(minidlna, auth, minidlna_verify).files()

def find_minidlna_paths(user_id):
    return list(map(lambda item: item['path'], find_minidlna_files(user_id)))

def find_orphan_files():
    dlna = find_minidlna_files()
    orphan = [];
    catalogue = [];

    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""SELECT path FROM minicloud_multimedia ORDER BY path""")
            for result in cursor.fetchall():
                catalogue.append(result['path'])

        except:
            pass

    for item in dlna:
        if not item['path'] in catalogue: orphan.append(item)

    return orphan

@multimedia.route('/')
@login_required
def show():
    paths = find_minidlna_paths(int(current_user.id))
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            multimedia = []

            cursor.execute("""
              SELECT DISTINCT ON (category) category, count(category) AS count,
                json_agg(json_build_object('title', title, 'director', director, 'actors', actors, 'year', year, 'path', path, 'uuid', uuid, 'mime', mime, 'capture', capture) ORDER BY year, title ASC) AS media
              FROM minicloud_multimedia GROUP BY category ORDER BY category ASC
              """)

            for fetch in cursor.fetchall():
                media = list(filter(lambda media: media['path'] in paths, fetch['media']))
                if len(media) > 0:
                    obj = { 'category': fetch['category']
                          , 'count': len(media)
                          , 'media': media
                          }

                    multimedia.append(obj)

            return render_template( "multimedia/show.html"
                                  , multimedia = multimedia
                                  , config = config
                                  )

        except Exception as e:
            app.logger.error('Show in multimedia failed: %s' % str(e))
            pass

    abort(500)

@multimedia.route('/view/<uuid>')
@login_required
def view(uuid):
    dlna = find_minidlna_files(current_user.id)
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              SELECT a.id AS id, a.uuid AS uuid, category, title, description, director, actors, path, year, mime, media AS status FROM minicloud_multimedia AS a
                LEFT JOIN minicloud_users AS b ON (b.id = %s)
              WHERE a.uuid = %s LIMIT 1
              """, [int(current_user.id), uuid])

            proxy = False
            media = cursor.fetchone()
            sources = list(filter(lambda item: item['path'] == media['path'], dlna))
            app.logger.info('Open multimedia %s' % media['path'])

            if minidlna_proxy_host:
                for i, val in enumerate(sources):
                    sources[i]['url'] = re.sub('^http.\/\/[^:]*:8200', minidlna_proxy_host, val['url'])
                    app.logger.info('Source: %s' % sources[i]['url'])

            if minidlna_proxy_port:
                for i, val in enumerate(sources):
                    sources[i]['url'] = val['url'].replace('8200', minidlna_proxy_port)
                    app.logger.info('Source: %s' % sources[i]['url'])

            if minidlna_proxy_host or minidlna_proxy_port:
                proxy = True;

            if len(sources) > 0:
                return render_template( "multimedia/view.html"
                                      , media = media
                                      , config = config
                                      , sources = sources
                                      , proxy = proxy
                                      )

        except Exception as e:
            app.logger.error('View in multimedia failed: %s' % str(e))

    abort(500)

@multimedia.route('/indexing', methods = ["GET"])
@login_required
@admin_required
def indexing():
    dlna = find_orphan_files()
    return render_template( "multimedia/indexing.html"
                          , config = config
                          , items = dlna
                          , categories = get_categories()
                          )

@multimedia.route('/add', methods = ["POST"])
@login_required
@admin_required
def add():
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        title = request.form['title']
        lype = request.form['type']
        url = request.form['url']
        path = request.form['path']
        size = request.form['size']
        year = request.form['year']
        mime = request.form['mime']
        director = request.form.get('director')
        category = request.form.get('category')
        description = request.form.get('description')

        if not category: category = title
        if not description: description = ''
        if not director: director = 'Generic'

        try:
            cursor.execute("""
              INSERT INTO minicloud_multimedia
                (category, type, title, description, path, mime, size, director, year) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
              """, [ category
                   , lype
                   , title
                   , description
                   , path
                   , mime
                   , size
                   , director
                   , year
                   ])

            g.db.commit()
            flash(['Media added'], 'info')

        except:
            app.logger.error('Indexing in multimedia failed: %s' % str(e))
            flash(['Indexing failed'], 'error')
            g.db.rollback()

    return redirect("/multimedia")

@multimedia.route('/edit/<uuid>', methods = ["POST"])
@login_required
@admin_required
def edit(uuid):
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        title = request.form['title']
        lype = request.form['type']
        year = request.form['year']
        director = request.form.get('director')
        category = request.form.get('category')
        description = request.form.get('description')
        tags = request.form.get('tags')
        actors = []
        actors = tags.split(',')

        if not category: category = title
        if not description: description = ''
        if not director: director = 'Generic'

        try:
            cursor.execute("""
              UPDATE minicloud_multimedia SET
                category = %s, type = %s, year = %s, title = %s, description = %s, director = %s, actors = %s
              WHERE uuid = %s
              """, [ category
                   , lype
                   , year
                   , title
                   , description
                   , director
                   , actors
                   , uuid
                   ])

            g.db.commit()
            flash(['Media modified'], 'info')

        except Exception as e:
            app.logger.error('Edit in multimedia failed: %s' % str(e))
            g.db.rollback()
    
    return redirect("/multimedia")

@multimedia.route('/delete/<uuid>', methods = ["POST"])
@login_required
@admin_required
def delete(uuid):
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              DELETE FROM minicloud_multimedia WHERE uuid = %s
            """, [ uuid ])

            g.db.commit()
            flash(['Media removed'], 'info')

        except Exception:
            app.logger.error('Deletion in multimedia failed: %s' % str(e))
            g.db.rollback()

    return redirect("/multimedia")

@multimedia.route('/capture/<uuid>', methods = ["POST"])
@login_required
@admin_required
def capture(uuid):
    name, value = next(((name, value) for name,value in request.headers if name == 'X-Type'), (None, None))
    ajax = True if value == 'Ajax' else False
    canvas = request.form['canvas']
    messages = []

    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              UPDATE minicloud_multimedia SET capture = %s
              WHERE uuid = %s
              """, [ canvas, uuid ])

            g.db.commit()
            messages.append('Capture saved')

            if ajax:
                return make_response(jsonify(messages), 200)

            else:
                flash(messages, 'info')
                return redirect(url_for('multimedia.view', uuid=uuid))

        except Exception as e:
            g.db.rollback()

    abort(500)
