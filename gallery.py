import psycopg2, psycopg2.extras, io, time, os, re, functools
from PIL import Image, ImageOps
from flask import Blueprint, url_for, redirect, g, render_template, send_file, request, flash, abort
from flask_login import login_required, current_user
from config import app
from helpers import get_categories, get_stream
from mimes import MIME_SUFFIX

gallery = Blueprint('gallery', __name__)

def find_gallery_files(user_id):
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              SELECT user_id, uploads_id FROM minicloud_gallery
              WHERE user_id = %s
            """, [ user_id ])

            items = cursor.fetchall()
            return items

        except Warning:
            g.db.rollback()
            # Log message e

    return []

def find_orphan_files(user_id):
    orphans = []
    files = list(map(lambda item: '%s$%s' % (item['user_id'], item['uploads_id']), find_gallery_files(user_id)))

    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              SELECT * FROM minicloud_uploads
              WHERE user_id = %s and type = 1 and (mime = 'image/jpeg' or mime = 'image/png')
            """, [ user_id ])

            for item in cursor.fetchall():
                pattern = '%s$%s' % (item['user_id'], item['id'])
                if not pattern in files:
                    orphans.append(item)

        except Warning:
            g.db.rollback()
            # Log message e

    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        for orphan in orphans:
            lo = g.db.lobject(orphan['lo'], 'rb')
            upload = lo.read()
            lo.close()

            data = pillow_thumbnail(upload, orphan['mime'])
            size = len(data)

            try:
                cursor.execute("""
                  INSERT INTO minicloud_gallery (uploads_id, user_id, category, title, thumbnail_data, thumbnail_mime, thumbnail_size)
                  VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, ( orphan['id']
                     , user_id
                     , 'Uploaded'
                     , orphan['title']
                     , psycopg2.Binary(data)
                     , orphan['mime']
                     , size
                     ))

                g.db.commit()

            except Warning:
                g.db.rollback()
                # Log message e

    return orphans

@gallery.route("/")
@login_required
def show():
    orphans = find_orphan_files(int(current_user.id))
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
      try:

        cursor.execute("""
          SELECT category AS name, json_agg(json_build_object('id', id, 'uid', uid, 'title', title) ORDER BY updated_at ASC) AS files
          FROM minicloud_gallery WHERE user_id = %s GROUP BY category ORDER BY category ASC
          """, [ int(current_user.id) ])

        files = cursor.fetchall()

        return render_template( "gallery/show.html"
                              , files = files
                              , categories = get_categories()
                              )

      except Exception as e:
          app.logger.error('Show in gallery failed: %s' % str(e))
          g.db.rollback()

    abort(500)

@gallery.route("/edit/<uid>", methods = ["GET", "POST"])
@login_required
def edit(uid):
    if request.method == "GET":
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT id, title, description, uid, category FROM minicloud_gallery
              WHERE user_id = %s AND uid = %s LIMIT 1
              """, [int(current_user.id), uid])

            file = cursor.fetchone()

        return render_template( "gallery/edit.html"
                              , categories = get_categories()
                              , file = file
                              )

    if request.method == "POST":
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']

        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            try:
                cursor.execute("""
                    UPDATE minicloud_gallery
                      SET title = %s, description = %s, category = %s
                    WHERE user_id = %s AND uid = %s
                    """, [title, description,  category, int(current_user.id), uid])

                g.db.commit()
                flash(['File modified'], 'info')

            except Exception as e:
                app.logger.error('Edit in gallery failed: %s' % str(e))
                g.db.rollback()
                flash(['Edit failed'], 'error')

        return redirect(url_for('gallery.show'))

    abort(501)

@gallery.route("/delete/<uid>", methods = ["POST"])
@login_required
def delete(uid):
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              DELETE FROM minicloud_uploads AS a
                USING minicloud_gallery AS b
              WHERE b.user_id = %s AND b.uid = %s AND a.user_id = b.user_id AND a.id = b.uploads_id RETURNING lo
            """, [ int(current_user.id), uid])

            data = cursor.fetchone()
            lo = g.db.lobject(data['lo'], 'wb')
            lo.unlink()
            lo.close()

            g.db.commit()
            flash(['File deleted'], 'info')

        except Exception as e:
            app.logger.error('Deletion in gallery failed: %s' % str(e))
            g.db.rollback()
            flash(['Deletion failed'], 'error')

    return redirect(url_for("gallery.show"))

@gallery.route("/download/<uid>", methods = ["GET"])
@login_required
def download(uid):
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              SELECT b.uid AS uid, b.lo AS lo, b.size AS size, b.mime AS mime FROM minicloud_gallery AS a
                LEFT JOIN minicloud_uploads AS b ON (b.id = a.uploads_id AND b.user_id = a.user_id)
              WHERE a.user_id = %s AND a.uid = %s LIMIT 1;
              """, [int(current_user.id), uid])

            data = cursor.fetchone()
            suffix = MIME_SUFFIX[data['mime']] if data['mime'] in MIME_SUFFIX else 'unknwon'
            filename = '%s.%s' % (data['uid'], suffix)

            return get_stream(request, filename, data['lo'], data['mime'], data['size'])

        except Exception as e:
            app.logger.error('Download in gallery failed: %s' % str(e))
            g.db.rollback()

    abort(500)

@gallery.route("/thumbnail/<uid>", methods = ["GET"])
@login_required
def thumbnail(uid):
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              SELECT uid, thumbnail_mime, thumbnail_data FROM minicloud_gallery
              WHERE user_id = %s AND uid = %s LIMIT 1;
              """, [int(current_user.id), uid])

            data = cursor.fetchone()
            suffix = MIME_SUFFIX[data['thumbnail_mime']] if data['thumbnail_mime'] in MIME_SUFFIX else 'unknwon'

            return send_file( io.BytesIO(data["thumbnail_data"])
                            , mimetype = data["thumbnail_mime"]
                            , as_attachment = True
                            , attachment_filename = '%s.%s' % (data['uid'], suffix)
                            , cache_timeout = 0
                            )

        except Exception as e:
            app.logger.error('Thumbnail in gallery failed: %s' % str(e))
            g.db.rollback()

    abort(500)

def pillow_orientation(upload, mimetype):
    try:
        image = io.BytesIO()
        fd = Image.open(io.BytesIO(upload))
        fd = ImageOps.exif_transpose(fd)

        if mimetype == 'image/jpeg': fd.save(image, format = "JPEG")
        if mimetype == 'image/png': fd.save(image, format = "PNG")

        return image.getvalue()

    except Warning:
        return upload
        # Log message e

def pillow_thumbnail(upload, mimetype):
    try:
        thumbnail = io.BytesIO()
        image = Image.open(io.BytesIO(upload))
        image.thumbnail((300, 300))

        if mimetype == 'image/jpeg': image.save(thumbnail, format = "JPEG")
        if mimetype == 'image/png': image.save(thumbnail, format = "PNG")

        return thumbnail.getvalue()

    except Warning:
        return upload
        # Log message e

@gallery.route('/diashow')
@login_required
def diashow():
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              SELECT * FROM minicloud_diashow
              WHERE user_id = %s ORDER BY created_at DESC
              """, [ int(current_user.id) ])

            diashows = cursor.fetchall()

            return render_template( "gallery/diashow.html"
                                  , diashows = diashows
                                  , categories = get_categories()
                                  )

        except Exception as e:
            app.logger.error('Show in diashow failed: %s' % str(e))
            g.db.rollback()

    abort(500)

@gallery.route("/diashow/play/<uuid>", methods = ["GET"])
def diashow_play(uuid):
   diashow = None

   try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT a.uuid, json_agg(json_build_object('uid', b.uid, 'title', b.title, 'description', b.description) ORDER BY b.updated_at ASC) AS files
              FROM minicloud_diashow AS a
              INNER JOIN minicloud_gallery AS b ON (a.user_id = b.user_id AND a.category = b.category)
              WHERE a.uuid = %s GROUP BY (a.uuid) LIMIT 1;
              """, [uuid])

            diashow = cursor.fetchone()

            if not diashow:
                flash(['No files found!'], 'error')
                raise Exception('No files found')

   except Exception as e:
       app.logger.error('Play in diashow failed: %s' % str(e))
       g.db.rollback()
       return redirect(url_for('gallery.diashow'))

   return render_template("gallery/diashow_play.html", diashow = diashow)

@gallery.route("/diashow/<uuid>/download/<uid>", methods = ["GET"])
def diashow_download(uuid, uid):
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
                SELECT c.uid AS uid, c.lo AS lo, c.size AS size, c.mime AS mime FROM minicloud_diashow AS a
                LEFT JOIN minicloud_gallery AS b ON (a.user_id = b.user_id AND b.uid = %s)
                LEFT JOIN minicloud_uploads AS c ON (b.user_id = c.user_id AND b.uploads_id = c.id)
                WHERE a.uuid = %s LIMIT 1;
                """, [uid, uuid])

            data = cursor.fetchone()
            suffix = MIME_SUFFIX[data['mime']] if data['mime'] in MIME_SUFFIX else 'unknwon'
            filename = '%s.%s' % (data['uid'], suffix)

            return get_stream(request, filename, data['lo'], data['mime'], data['size'])

        except Exception as e:
            app.logger.error('Download in diashow failed: %s' % str(e))
            g.db.rollback()

    abort(500)

@gallery.route("/diashow/add", methods = ["POST"])
@login_required
def diashow_add():
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        category = request.form['category']

        try:
            cursor.execute("""
              INSERT INTO minicloud_diashow (user_id, category)
              VALUES (%s, %s)
              """, [ int(current_user.id)
                   , category
                   ])

            g.db.commit()
            flash(['Slide show added'], 'info')

        except Exception as e:
            g.db.rollback()
            app.logger.error('Adding in slide show failed: %s' % str(e))
            flash(['Adding failed'], 'error')

    return redirect(url_for('gallery.diashow'))

@gallery.route("/diashow/delete/<uid>", methods = ["POST"])
@login_required
def diashow_delete(uid):
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              DELETE FROM minicloud_diashow
              WHERE user_id = %s AND uid = %s
              """, [ int(current_user.id), uid] )

            g.db.commit()
            flash(['Slide show deleted'], 'info')

        except Exception as e:
            app.logger.error('Deletion in diashow failed: %s' % str(e))
            g.db.rollback()
            flash(['Deletion failed'], 'error')

    return redirect(url_for('gallery.diashow'))
