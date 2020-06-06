import psycopg2, psycopg2.extras, uuid, re, io, glob, os.path
from datetime import datetime
from dateutil import parser
from flask import Blueprint, g, request, render_template, url_for, redirect, flash, send_file, send_from_directory, abort
from users import login_required, admin_required, current_user
from contextlib import closing
from config import config
from pathlib import Path

tools = Blueprint('tools', __name__)
folder = '/var/minicloud/multimedia'

def find_orphan_files():
    orphan = [];
    catalogue = [];
    files = list(map(lambda item: str(item), list(Path(folder).rglob('*.*'))))

    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""SELECT path FROM minicloud_multimedia ORDER BY path""")
            for fd in cursor.fetchall():
                catalogue.append(fd['path'])

        except Warning:
            pass

    for found in files:
        if not found in catalogue: orphan.append(found)

    return orphan

@tools.route('/multimedia')
@login_required
def multimedia_show():
    # files = list(Path(folder).rglob('*.*'))
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            print('---')
            print(find_orphan_files())
            print('---')
            multimedia = []

            cursor.execute("""
                SELECT DISTINCT ON (category) category, count(category) AS count,
                json_agg(json_build_object('title', title, 'path', path, 'uuid', uuid, 'mimetype', mime) ORDER BY created_at ASC) AS media
                FROM minicloud_multimedia GROUP BY category ORDER BY category ASC
                """)

            for fetch in cursor.fetchall():
                media = list(filter(lambda media: os.access(media['path'], os.R_OK), fetch['media']))
                if len(media) > 0:
                    obj = { 'category': fetch['category']
                          , 'count': len(media)
                          , 'media': media
                          }

                    multimedia.append(obj)

            return render_template( "tools/multimedia_show.html"
                                  , multimedia = multimedia
                                  , config = config
                                  )
        except Warning:
            pass

    abort(500)

@tools.route('/multimedia/view/<uuid>')
@login_required
def multimedia_view(uuid):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                SELECT title, uuid, path, mime AS mimetype FROM minicloud_multimedia
                WHERE uuid = %s LIMIT 1
                """, [uuid])

            media = cursor.fetchone()
            return render_template( "tools/multimedia_view.html"
                                  , media = media
                                  , config = config
                                  )
        except Warning:
            pass

    abort(500)

@tools.route('/multimedia/play/<uuid>')
@login_required
def multimedia_play(uuid):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                SELECT path, mime AS mimetype FROM minicloud_multimedia
                WHERE uuid = %s LIMIT 1
                """, [uuid])

            media = cursor.fetchone()
            return send_from_directory( os.path.dirname(media['path'])
                                      , os.path.basename(media['path'])
                                      , mimetype = media['mimetype'])

        except Warning:
            pass

    abort(500)

@tools.route('/diashow')
@login_required
def diashow_show():
    diashows = []
    categories = []
    users = []

    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:

        try:
            cursor.execute("""
                SELECT * FROM minicloud_diashow
                  WHERE type = %s AND user_id = %s ORDER BY created_at DESC
                """, ['diashow', int(current_user.id)])

            diashows = cursor.fetchall()

            cursor.execute("""
                SELECT DISTINCT category AS title FROM minicloud_files
                  WHERE user_id = %s
                GROUP BY category ORDER BY title ASC;
                """, [int(current_user.id)])
            
            categories = cursor.fetchall()

            cursor.execute("""
                SELECT id, name FROM minicloud_users
                WHERE id <> %s AND NOT disabled ORDER BY name ASC
                """, [int(current_user.id)])
            
            users = cursor.fetchall()

            return render_template( "tools/diashow_show.html"
                                  , diashows = diashows
                                  , categories = categories
                                  , users = users
                                  )

        except Warning:
            g.db.rollback()

    abort(500)

@tools.route("/diashow/add", methods = ["POST"])
@login_required
def diashow_add():
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        title = request.form['title']
        # description = request.form['description']
        category = request.form['category']

        try:
            cursor.execute("""
                INSERT INTO minicloud_diashow
                (type, title, description, user_id, category)
                VALUES (%s, %s, %s, %s, %s)
                """, [ 'diashow'
                     , title
                     , ''
                     , int(current_user.id)
                     , category
                     ])

            g.db.commit()
            flash(['Diashow added'], 'info')

        except Warning:
            g.db.rollback()

    return redirect("/tools/diashow")

@tools.route("/diashow/play/<uuid>", methods = ["GET"])
def diashow_play(uuid):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
              SELECT a.uuid, a.title, json_agg(json_build_object('uuid', b.uid, 'title', b.title, 'description', b.description) ORDER BY b.updated_at ASC) AS files
              FROM minicloud_diashow AS a INNER JOIN minicloud_files AS b ON (a.user_id = b.user_id AND a.category = b.category)
              WHERE a.uuid = %s GROUP BY (a.uuid, a.title) LIMIT 1;
              """, [uuid])
            
            diashow = cursor.fetchone()
            return render_template( "tools/diashow_play.html", diashow = diashow)

        except Warning:
            g.db.rollback()

    abort(500)

@tools.route("/diashow/<diashow>/download/<uid>", methods = ["GET"])
def diashow_download(diashow, uid):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                SELECT b.oid AS oid, b.data_mime AS mime FROM minicloud_diashow AS a
                LEFT JOIN minicloud_files AS b ON (a.user_id = b.user_id AND b.uid = %s)
                WHERE a.uuid = %s LIMIT 1;
                """, [uid, diashow])
        
            data = cursor.fetchone()
            lobj = g.db.lobject(int(data['oid']), 'rb')
            stream = lobj.read()
            lobj.close()

            return send_file( io.BytesIO(stream)
                            , mimetype = data['mime']
                            , as_attachment = False
                            )

        except Warning:
            g.db.rollback()

    abort(500)

@tools.route("/diashow/delete/<uid>", methods = ["POST"])
@login_required
def diashow_delete(uid):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                DELETE FROM minicloud_diashow
                WHERE type = %s AND user_id = %s AND uid = %s
                """, ['diashow', int(current_user.id), uid])

            g.db.commit()
            flash(['Diashow removed'], 'info')

        except Warning:
            g.db.rollback()

    return redirect("/tools/diashow")
