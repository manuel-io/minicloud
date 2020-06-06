import psycopg2, psycopg2.extras, io, time, os, re
from PIL import Image, ImageOps
from flask import Blueprint, url_for, redirect, g, render_template, send_file, request, flash, send_from_directory, Response, abort
from flask_login import UserMixin, login_required, current_user
from contextlib import closing
from config import config, MIME_SUFFIX

files = Blueprint('files', __name__)

@files.route("/")
@login_required
def show():
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:

        cursor.execute("""
            SELECT category AS name, json_agg(json_build_object('id', id, 'uid', uid, 'title', title, 'mime', data_mime) ORDER BY updated_at ASC) AS files
            FROM minicloud_files WHERE user_id = %s GROUP BY category ORDER BY category ASC
              """, [int(current_user.id)])

        categories = cursor.fetchall()

        return render_template( "files/show.html"
                              , config = config
                              , categories = categories
                              )

@files.route("/edit/<index>", methods = ["GET", "POST"])
@login_required
def edit(index):
    if request.method == "GET":
        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
            cursor.execute("""
                SELECT id, title, description, uid, category, data_mime AS mime FROM minicloud_files
                WHERE user_id = %s AND uid = %s LIMIT 1
                """, [int(current_user.id), index])
                
            file = cursor.fetchone()
    
        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
            cursor.execute("""
                SELECT a.uid, a.shared_type, 'public' AS target FROM minicloud_shared AS a
                  WHERE user_id = %s AND file_id = %s AND shared_type = '1'
                UNION ALL SELECT b.uid, b.shared_type, 'cloud' FROM minicloud_shared AS b
                  WHERE user_id = %s AND file_id = %s AND  shared_type = '2'
                UNION ALL SELECT c.uid, c.shared_type, d.name AS target FROM minicloud_shared AS c
                  LEFT JOIN minicloud_users AS d ON (c.shared_id = d.id)
                  WHERE user_id = %s AND file_id = %s AND shared_type = '3';

                """, [ int(current_user.id), file['id']
                     , int(current_user.id), file['id']
                     , int(current_user.id), file['id']
                     ])
                
            shared = cursor.fetchall()
    
        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
            cursor.execute("""
                SELECT DISTINCT category AS title FROM minicloud_files
                  WHERE user_id = %s
                UNION SELECT DISTINCT category AS title FROM minicloud_tasks
                  WHERE user_id = %s
                GROUP BY title ORDER BY title ASC;
                """, [ int(current_user.id)
                     , int(current_user.id)
                     ])
            
            categories = cursor.fetchall()

        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
            cursor.execute("""
                SELECT id, name FROM minicloud_users
                WHERE id <> %s AND NOT disabled ORDER BY name ASC
                """, [int(current_user.id)])
            
            users = cursor.fetchall()
    
        return render_template( "files/edit.html"
                              , config = config
                              , categories = categories
                              , users = users
                              , shared = shared
                              , file = file
                              )
                              
    if request.method == "POST":
        title = request.form['title'] 
        description = request.form['description'] 
        category = request.form['category']

        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
            try:

                cursor.execute("""
                    UPDATE minicloud_files
                    SET title = %s, description = %s, category = %s
                    WHERE user_id = %s AND uid = %s
                    """, [title, description,  category, int(current_user.id), index])

                g.db.commit()
                flash(['File modified'], 'info')

            except:
                g.db.rollback()
        
        return redirect("/files")

@files.route("/delete/<value>", methods = ["POST"])
@login_required
def delete(value):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                DELETE FROM minicloud_files
                WHERE user_id = %s AND uid = %s RETURNING oid
                """,  [current_user.id, value])

            data = cursor.fetchone()
            lobj = g.db.lobject(int(data['oid']), 'wb')
            lobj.unlink()

            g.db.commit()
            flash(['File removed'], 'info')

        except:
            g.db.rollback()

    return redirect(url_for("index"))

@files.route("/upload", methods = ["POST"])
@login_required
def upload():
    f = request.files["file"]
    n = request.form["name"]

    upload = f.read()
    data_size = len(upload)
    mimetype = f.content_type
    thumbnail_mime = None
    thumbnail_data = None

    if mimetype in ["image/jpeg", "image/png"]:
        upload = pillow_orientation(upload, mimetype)
        data_size = len(upload)

    if mimetype in ["image/jpeg", "image/png"]:
        thumbnail_data = pillow_thumbnail(upload, mimetype)
        thumbnail_mime = mimetype

    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                INSERT INTO minicloud_files (user_id, category, title, data_size, data_mime, thumbnail_mime, thumbnail)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING oid
                """, ( int(current_user.id)
                     , 'Uploaded'
                     , n
                     , data_size
                     , mimetype
                     , thumbnail_mime
                     , psycopg2.Binary(thumbnail_data)
                     ))

            data = cursor.fetchone()
            lobj = g.db.lobject(0, 'w', int(data['oid']))
            write_size = lobj.write(upload)
            lobj.close()
            g.db.commit()
            flash(['File added'], 'info')

        except Warning:
            g.db.rollback()

    return redirect(url_for("index"))

def download_file(user_id, file_uid, print_uid = None):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                SELECT uid, oid, data_mime FROM minicloud_files
                WHERE user_id = %s AND uid = %s LIMIT 1;
                """, [user_id, file_uid])

            data = cursor.fetchone()
            lobj = g.db.lobject(int(data['oid']), 'rb')
            f = lobj.read()

            print_uid = print_uid if print_uid else data['uid']
            suffix = MIME_SUFFIX[data['data_mime']] if data['data_mime'] in MIME_SUFFIX else 'unknwon'

            return send_file( io.BytesIO(f)
                            , mimetype = data['data_mime']
                            , as_attachment = True
                            , attachment_filename = '%s.%s' % (print_uid, suffix)
                            )
        except Warning:
            g.db.rollback()

@files.route("/download/<uid>", methods = ["GET", "POST"])
@login_required
def download(uid):
    try:
        return download_file(int(current_user.id), uid)
    except:
        abort(500)

def pillow_orientation(upload, mimetype):
    try:
        image = io.BytesIO()
        fd = Image.open(io.BytesIO(upload))
        fd = ImageOps.exif_transpose(fd)

        if mimetype == 'image/jpeg': fd.save(image, format = "JPEG")
        if mimetype == 'image/png': fd.save(image, format = "PNG")

        return image.getvalue()

    except:
        return upload

def pillow_thumbnail(upload, mimetype):
    try:
        thumbnail = io.BytesIO()
        image = Image.open(io.BytesIO(upload))
        image.thumbnail((300, 300))
        
        if mimetype == 'image/jpeg': image.save(thumbnail, format = "JPEG")
        if mimetype == 'image/png': image.save(thumbnail, format = "PNG")
        
        return thumbnail.getvalue()

    except:
        return upload

def thumbnail_file(user_id, file_uid):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                SELECT uid, thumbnail_mime, thumbnail FROM minicloud_files
                WHERE user_id = %s AND uid = %s LIMIT 1;
                """, [user_id, file_uid])

            data = cursor.fetchone()

            return send_file( io.BytesIO(data["thumbnail"])
                            , mimetype = data["thumbnail_mime"]
                            , as_attachment = True
                            , attachment_filename = '%s.%s' % (data['uid'], '')
                            )

        except Warning:
            g.db.rollback()

@files.route("/thumbnail/<uid>", methods = ["GET"])
@login_required
def thumbnail(uid):
    try:
        return thumbnail_file(int(current_user.id), uid)
    except:
        abort(500)

def stream_file(user_id, file_uid, print_uid = None):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                SELECT uid, oid, data_mime, data_size FROM minicloud_files
                WHERE user_id = %s AND uid = %s LIMIT 1;
                """, [user_id, file_uid])

            data = cursor.fetchone()
            print_uid = print_uid if print_uid else data['uid']
            suffix = MIME_SUFFIX[data['data_mime']] if data['data_mime'] in MIME_SUFFIX else 'unknwon'
            filename = '%s.%s' % (print_uid, suffix)

            oid = int(data['oid'])
            data_mime = data['data_mime']
            data_size = int(data['data_size'])

            if request.headers.has_key("Range"):
                begin, end = 0, data_size - 1
                ranges = re.findall(r"\d+", request.headers["Range"])

                if ranges[0]:
                    begin = int(ranges[0])
                    length = end - begin + 1

                if len(ranges) > 1:
                    end = int(ranges[1])
                    length = end - begin + 1

                if begin > end: abort(416)

                lobj = g.db.lobject(oid, 'rb')
                lobj.seek(begin)
                stream = io.BytesIO(lobj.read(length))
                stream_size = stream.getbuffer().nbytes
                lobj.close()

                response = Response(stream, 206, mimetype=data_mime, direct_passthrough=True)
                response.headers.add('Accept-Ranges', 'bytes')
                response.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(begin, begin + length - 1, data_size))
                response.headers.add('Content-Length', str(length))
                response.headers.add('Content-Disposition', 'attachment', filename=filename)
                return response

            else:
                lobj = g.db.lobject(oid, 'rb')
                stream = io.BytesIO(lobj.read())
                stream_size = stream.getbuffer().nbytes
                length = stream_size
                lobj.close()

                response = Response(stream, 200, mimetype=data_mime, direct_passthrough=True)
                response.headers.add('Accept-Ranges', 'bytes')
                response.headers.add('Content-Length', str(length))
                response.headers.add('Content-Disposition', 'attachment', filename=filename)
                return response

        except Warning:
            g.db.rollback()

@files.route("/stream/<uid>", methods = ["GET"])
@login_required
def stream(uid):
    try:
        return stream_file(int(current_user.id), uid)
    except Warning:
        abort(500)
