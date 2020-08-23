import psycopg2, psycopg2.extras, uuid, re, io, glob, os.path, requests
import auths, filters
from datetime import datetime
from dateutil import parser
from flask import Blueprint, g, request, Response, render_template, url_for, redirect, jsonify, make_response, flash, send_file, send_from_directory, abort
from users import login_required, admin_required, current_user
from config import app, config
from pathlib import Path
from minidlna import MiniDLNA
from helpers import get_media_types

multimedia = Blueprint('multimedia', __name__)
base = Path('/var/minicloud/multimedia')
minidlna = os.environ['MINICLOUD_DLNA'] if 'MINICLOUD_DLNA' in os.environ else 'http://127.0.0.1:8290'
minidlna_verify = False if 'MINICLOUD_DLNA_NOVERIFY' in os.environ else True
minidlna_proxy_host = os.environ['MINICLOUD_DLNA_PROXY_HOST'] if 'MINICLOUD_DLNA_PROXY_HOST' in os.environ else None
minidlna_proxy_port = os.environ['MINICLOUD_DLNA_PROXY_PORT'] if 'MINICLOUD_DLNA_PROXY_PORT' in os.environ else None

def find_local_files():
    return list(map(lambda path: str(path.relative_to(base)), list(base.rglob('*.*'))))

def find_minidlna_files(auth):
    return MiniDLNA(minidlna, auth, minidlna_verify).files()

def find_minidlna_paths(auth):
    return list(map(lambda item: item['path'], find_minidlna_files(auth)))

def find_orphan_files(auth):
    dlna = find_minidlna_files(auth)
    orphan, catalogue = [[], []]

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""SELECT path FROM minicloud_multimedia ORDER BY path""")
            for result in cursor.fetchall():
                catalogue.append(result['path'])

    except Exception as e:
        pass

    for item in dlna:
        if not item['path'] in catalogue: orphan.append(item)

    return orphan

@multimedia.route('/')
@login_required
def show():
    ref = 'movies'
    auth = auths.generate(current_user.id)
    paths = find_minidlna_paths(auth)

    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    all_directors = filters.get_directors(ref)
    all_actors = filters.get_actors(ref)

    directors = []
    if 'director' in request.args.keys():
        directors = [ director for director in [ request.args.get('director').strip() ] if len(director) > 0 ]

    actors = []
    if 'actors' in request.args.keys():
        actors = [ tag.strip() for tag in request.args.get('actors').split(',') if len(tag.strip()) > 0 ]

    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            multimedia = []

            cursor.execute("""
              SELECT DISTINCT ON (category) category, count(category) AS count, json_agg(json_build_object('title', title, 'director', director, 'actors', actors, 'year', year, 'path', path, 'uuid', uuid, 'mime', mime, 'capture', capture) ORDER BY year, title ASC) AS media
              FROM minicloud_multimedia
              WHERE actors @> %s AND ARRAY[director] @> %s AND type = %s GROUP BY category ORDER BY category ASC
              """, [actors, directors, ref])

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
                                  , all_directors = all_directors
                                  , all_actors = all_actors
                                  , ref = ref
                                  , media_types = get_media_types()
                                  )

        except Exception as e:
            app.logger.error('Show in multimedia failed: %s' % str(e))

    abort(500)

@multimedia.route('/view/<uuid>')
@login_required
def view(uuid):
    ref = 'movies'
    auth = auths.generate(current_user.id)
    dlna = find_minidlna_files(auth)
    proxy, media = [False, None]

    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT a.id AS id, a.uuid AS uuid, category, title, description, director, actors, path, year, mime, media AS status FROM minicloud_multimedia AS a
              LEFT JOIN minicloud_users AS b ON (b.id = %s)
              WHERE a.uuid = %s LIMIT 1
              """, [int(current_user.id), uuid])

            media = cursor.fetchone()

        if not media:
            raise Exception('not found');

        sources = list(filter(lambda item: item['path'] == media['path'], dlna))
        app.logger.info('Multimedia %s' % media['path'])

        if minidlna_proxy_host:
            for i, val in enumerate(sources):
                sources[i]['url'] = re.sub('^http.\/\/[^:]*:8200', minidlna_proxy_host, val['url'])
                sources[i]['url'] = sources[i]['url'] + '?auth=%s' % auth
                app.logger.info('Source: %s' % sources[i]['url'])

        if minidlna_proxy_port:
            for i, val in enumerate(sources):
                sources[i]['url'] = val['url'].replace('8200', minidlna_proxy_port)
                sources[i]['url'] = sources[i]['url'] + '?auth=%s' % auth
                app.logger.info('Source: %s' % sources[i]['url'])

        if minidlna_proxy_host or minidlna_proxy_port:
            proxy = True;

        if len(sources) > 0:
            return render_template( "multimedia/view.html"
                                  , auth = auth
                                  , media = media
                                  , config = config
                                  , sources = sources
                                  , proxy = proxy
                                  , ref = ref
                                  )
        else:
            raise Exception('no sources')

    except Exception as e:
        app.logger.error('Multimedia (%s): %s' % (uuid, str(e)))

    return redirect("/multimedia")

@multimedia.route('/indexing', methods = ["GET"])
@login_required
@admin_required
def indexing():
    ref = 'movies'
    auth = auths.generate(current_user.id)
    dlna = find_orphan_files(auth)

    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    return render_template( "multimedia/indexing.html"
                          , config = config
                          , items = dlna
                          , media_types = get_media_types()
                          , ref = ref
                          )

@multimedia.route('/add', methods = ["POST"])
@login_required
@admin_required
def add():
    ref = 'movies'

    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        title = request.form['title']
        ref = request.form['ref']
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
                   , ref
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

        except Exception as e:
            app.logger.error('Indexing in multimedia failed: %s' % str(e))
            flash(['Indexing failed'], 'error')
            g.db.rollback()

    return redirect(url_for('multimedia.show', ref = ref))

@multimedia.route('/edit/<uuid>', methods = ["POST"])
@login_required
@admin_required
def edit(uuid):
    ref = 'movies'
    title = request.form['title']
    year = request.form['year']

    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    director = 'Generic'
    if 'director' in request.form.keys():
        director = request.form.get('director')

    category = title
    if 'category' in request.form.keys():
        category = request.form.get('category')

    description = ''
    if 'description' in request.form.keys():
        description = request.form.get('description')

    actors = []
    if 'tags' in request.form.keys():
        actors = [ tag.strip() for tag in request.form.get('tags').split(',') ]

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              UPDATE minicloud_multimedia
              SET category = %s, year = %s, title = %s, description = %s, director = %s, actors = %s
              WHERE uuid = %s
              """, [ category
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
        g.db.rollback()
        app.logger.error('Edit in multimedia failed: %s' % str(e))

    return redirect(url_for('multimedia.show', ref = ref))

@multimedia.route('/delete/<uuid>', methods = ["POST"])
@login_required
@admin_required
def delete(uuid):
    ref = 'movies'

    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              DELETE FROM minicloud_multimedia WHERE uuid = %s
              """, [ uuid ])

            g.db.commit()
            flash(['Media deleted'], 'info')

    except Exception as e:
        g.db.rollback()
        app.logger.error('Deletion in multimedia failed: %s' % str(e))

    return redirect(url_for('multimedia.show', ref = ref))

@multimedia.route('/capture/<uuid>', methods = ["POST"])
@login_required
@admin_required
def capture(uuid):
    name, value = next(((name, value) for name,value in request.headers if name == 'X-Type'), (None, None))
    ajax = True if value == 'Ajax' else False
    canvas = request.form['canvas']
    messages = []

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
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
        app.logger.error('Capture failed: %s' % str(e))

    abort(500)
