import psycopg2, psycopg2.extras, io, time, os, re, functools
from PIL import Image, ImageOps
from flask import Blueprint, url_for, redirect, g, render_template, send_file, request, flash, send_from_directory, Response, abort, make_response, jsonify
from flask_login import UserMixin, login_required, current_user
from config import config, MIME_SUFFIX
from helpers import get_categories, get_stream

uploads = Blueprint('uploads', __name__)

@uploads.route("/")
@login_required
def show():
    parent = request.args.get('parent')
    parent = int(parent) if parent and parent.isnumeric() else None
    backref = request.args.get('backref')
    backref = int(backref) if backref and backref.isnumeric() else None

    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            if parent:
              cursor.execute("""
                SELECT reference, backref, json_agg(json_build_object('id', id, 'uid', uid, 'title', title, 'size', div(size,1024), 'mime', mime, 'type', type) ORDER BY type, title ASC) AS childs
                  FROM minicloud_uploads
                WHERE user_id = %s AND reference = %s GROUP BY (reference, backref);
                """, [ int(current_user.id), parent ])

            else:
              cursor.execute("""
                SELECT reference, backref, json_agg(json_build_object('id', id, 'uid', uid, 'title', title, 'size', div(size, 1024), 'mime', mime, 'type', type) ORDER BY type, title ASC) AS childs
                  FROM minicloud_uploads
                WHERE user_id = %s AND reference IS NULL GROUP BY (reference, backref);
                """, [ int(current_user.id) ])

            directory = cursor.fetchone()
            if directory:
                parent = directory['reference']
                backref = directory['backref']

            return render_template("uploads/show.html", parent = parent, backref = backref, directory = directory)

        except Exception as e:
            g.db.rollback()
            # Log message e

    abort(500)

@uploads.route("/file/add", methods = ['POST'])
@login_required
def file_add():
    name, value = next(((name, value) for name,value in request.headers if name == 'X-Type'), (None, None))
    ajax = True if value == 'Ajax' else False
    messages = []
    count = 0
    uploads = request.files.getlist('uploads')
    parent = request.form['parent']
    parent = int(parent) if parent and parent.isnumeric() else None
    backref = request.form['backref']
    backref = int(backref) if backref and backref.isnumeric() else None

    for upload in uploads:
        title = upload.filename
        mime = upload.content_type
        content = upload.read()
        size = len(content)

        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            try:
                cursor.execute("""
                  INSERT INTO minicloud_uploads (user_id, reference, backref, type, title, size, mime)
                  VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING oid
                  """, [ int(current_user.id)
                       , parent
                       , backref
                       , 1
                       , title
                       , size
                       , mime
                       ])

                data = cursor.fetchone()
                oid = g.db.lobject(0, 'w', int(data['oid']))
                write = oid.write(content)

                cursor.execute("""
                  UPDATE minicloud_uploads SET lo = %s
                  WHERE user_id = %s AND oid = %s
                  """, [ int(data['oid'])
                       , int(current_user.id)
                       , int(data['oid'])
                       ])

                g.db.commit()
                count = count + 1

            except Warning:
                g.db.rollback()
                # Log message e

    messages.append('%s of %s files uploaded' % (count, len(uploads)))

    if ajax:
        return make_response(jsonify(messages), 200)

    else:
        flash(messages, 'info')
        return redirect(url_for('uploads.show', parent=parent))

@uploads.route("/download/<uid>", methods = ['GET'])
@login_required
def download(uid):
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              SELECT uid AS name, oid, mime, size FROM minicloud_uploads
              WHERE user_id = %s AND uid = %s LIMIT 1;
              """, [int(current_user.id), uid])

            data = cursor.fetchone()
            suffix = MIME_SUFFIX[data['mime']] if data['mime'] in MIME_SUFFIX else 'unknwon'
            filename = '%s.%s' % (data['name'], suffix)
            oid = int(data['oid'])
            mime = data['mime']
            size = int(data['size'])

            return get_stream(request, filename, oid, mime, size)

        except Exception as e:
            g.db.rollback()
            # Log message e

    abort(500)

@uploads.route("/delete/<uid>", methods = ['POST'])
@login_required
def delete(uid):
    parent = request.form['parent']
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              SELECT count(a.reference) AS count FROM minicloud_uploads AS a
                LEFT JOIN minicloud_uploads AS b ON (b.uid = %s AND b.user_id = %s)
              WHERE a.reference = b.id AND a.user_id = %s
              """, [ uid, int(current_user.id), int(current_user.id) ])

            data = cursor.fetchone()
            if data['count'] > 0:
                flash(['Object has some references'], 'error')
                return redirect(url_for('uploads.show', parent=parent))

            cursor.execute("""
              DELETE FROM minicloud_uploads
              WHERE user_id = %s AND uid = %s RETURNING size, oid
              """, [ int(current_user.id), uid ])

            data = cursor.fetchone()
            if data['size'] > 0:
                oid = g.db.lobject(int(data['oid']), 'wb')
                oid.unlink()
                oid.close()

            g.db.commit()
            flash(['Object deleted'], 'info')

        except Exception as e:
            g.db.rollback()
            flash(['Failed :-('], 'error')

    return redirect(url_for('uploads.show', parent=parent))

@uploads.route("/dir/add", methods = ['POST'])
@login_required
def dir_add():
    title = request.form['title']
    parent = request.form['parent']
    parent = int(parent) if parent and parent.isnumeric() else None
    backref = request.form['backref']
    backref = int(backref) if backref and backref.isnumeric() else None

    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              INSERT INTO minicloud_uploads (user_id, reference, backref, type, title, size, mime)
              VALUES (%s, %s, %s, %s, %s, %s, %s)
              """, [ int(current_user.id)
                   , parent
                   , backref
                   , 0
                   , title
                   , 0
                   , 'directory'
                   ])

            g.db.commit()
            flash(['Dir added'], 'info')

        except Exception as e:
            g.db.rollback()
            flash(['Failed :-('], 'error')

    return redirect(url_for('uploads.show', parent=parent))
