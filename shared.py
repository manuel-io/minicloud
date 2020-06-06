import psycopg2, psycopg2.extras, uuid, re, io
from datetime import datetime
from dateutil import parser
from flask import Blueprint, g, request, render_template, url_for, redirect, flash, send_file, abort
from users import login_required, admin_required, current_user
from contextlib import closing
from config import config, MIME_SUFFIX
from files import download_file, stream_file, thumbnail_file

shared = Blueprint('shared', __name__)
SHARED_PUBLIC = 1
SHARED_CLOUD  = 2
SHARED_USER   = 3

@shared.route('/')
@login_required
def show():
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        cursor.execute("""
            SELECT DISTINCT ON (username) username,
            json_agg(json_build_object('uid', uid, 'title', title, 'mime', mime, 'type', type)) AS files FROM
              (SELECT DISTINCT ON (file_uid) file_uid, username, uid, title, mime, type FROM
                (SELECT DISTINCT ON (b.uid) b.uid AS file_uid, a.uid, c.name AS username, b.title, b.data_mime AS mime, a.shared_type AS type FROM minicloud_shared AS a
                   LEFT JOIN minicloud_files AS b ON (a.file_id = b.id)
                   LEFT JOIN minicloud_users AS c ON (a.user_id = c.id)
                WHERE a.user_id <> %s AND a.shared_type = %s UNION
                SELECT DISTINCT ON (b.uid) b.uid AS file_uid, a.uid, c.name AS username, b.title, b.data_mime AS mime, a.shared_type AS type FROM minicloud_shared AS a
                   LEFT JOIN minicloud_files AS b ON (a.file_id = b.id) 
                   LEFT JOIN minicloud_users AS c ON (a.user_id = c.id)
                WHERE a.user_id <> %s AND a.shared_type = %s UNION
                SELECT DISTINCT ON (b.uid) b.uid AS file_uid, a.uid, c.name AS username, b.title, b.data_mime AS mime, a.shared_type AS type FROM minicloud_shared AS a
                   LEFT JOIN minicloud_files AS b ON (a.file_id = b.id)
                   LEFT JOIN minicloud_users AS c ON (a.user_id = c.id)
                WHERE a.user_id <> %s AND  a.shared_type = %s AND a.shared_id = %s ORDER BY file_uid
              ) q) r GROUP BY username ORDER BY username ASC
            """, [ int(current_user.id)
                 , SHARED_PUBLIC
                 , int(current_user.id)
                 , SHARED_CLOUD
                 , int(current_user.id)
                 , SHARED_USER
                 , int(current_user.id)
                 ])

        shared = cursor.fetchall()

    return render_template("shared/show.html", config = config, shared = shared)

@shared.route('/view/<uid>', methods = ['GET', 'POST'])
@login_required
def view(uid):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                SELECT b.title AS title, a.uid AS uid, b.data_mime AS mime FROM minicloud_shared AS a
                LEFT JOIN minicloud_files AS b ON (file_id = b.id)
                WHERE a.uid = %s LIMIT 1;
                """, [uid])

            shared = cursor.fetchone()
            return render_template("shared/view.html", config = config, shared = shared)

        except Warning:
            pass

    abort(500)

@shared.route('/delete/<uid>', methods = ['POST'])
@login_required
def delete(uid):
    file_uid = request.form['file_uid']
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                DELETE FROM minicloud_shared
                WHERE user_id = %s AND uid = %s
            """, [int(current_user.id), uid])

            g.db.commit()
            flash(['File unshared'], 'info')

        except:
            g.db.rollback()

    return redirect("/files/edit/%s" % file_uid)

@shared.route('/add/<uid>', methods = ['POST'])
@login_required
def add(uid):
    file_id = request.form['file_id']
    file_uid = request.form['file_uid']
    shared_type = request.form['shared_type']
   
    shared_type = 1 if shared_type == 'public' else 2 if shared_type == 'cloud' else 3
    shared_id = request.form['shared_id'] if shared_type == 3 else int(current_user.id)
    
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                INSERT INTO minicloud_shared
                (user_id, file_id, file_uid, shared_id, shared_type)
                VALUES (%s, %s, %s, %s, %s)
                """, [ int(current_user.id)
                     , file_id
                     , file_uid
                     , shared_id
                     , shared_type
                     ])
            
            g.db.commit()
            msg = [ 'File shared with the public'
                  , 'File shared within cloud'
                  , 'File shared a user'
                  ]

            flash([msg[shared_type - 1]], 'info')

        except:
            g.db.rollback()

    return redirect("/files/edit/%s" % uid)

@shared.route("/thumbnail/<uid>", methods = ["GET"])
@login_required
def thumbnail(uid):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                SELECT * FROM minicloud_shared
                WHERE uid = %s LIMIT 1;
                """, [uid])
        
            shared = cursor.fetchone()

            if shared['shared_type'] == SHARED_PUBLIC:
                cursor.execute("""
                    SELECT b.thumbnail_mime AS mime, b.thumbnail AS data
                    FROM minicloud_shared AS a
                    LEFT JOIN minicloud_files AS b ON (a.file_id = b.id)
                    WHERE a.id = %s AND a.shared_type= %s LIMIT 1
                    """, [shared['id'], shared['shared_type']])

            if shared['shared_type'] == SHARED_CLOUD:
                cursor.execute("""
                    SELECT b.thumbnail_mime AS mime, b.thumbnail AS data
                    FROM minicloud_shared AS a
                    LEFT JOIN minicloud_files AS b ON (a.file_id = b.id)
                    WHERE a.id = %s AND a.shared_type= %s LIMIT 1
                    """, [shared['id'], shared['shared_type']])

            if shared['shared_type'] == SHARED_USER:
                cursor.execute("""
                    SELECT b.thumbnail_mime AS mime, b.thumbnail AS data
                    FROM minicloud_shared AS a
                    LEFT JOIN minicloud_files AS b ON (a.file_uid = b.uid)
                    WHERE a.id = %s AND a.shared_id = %s AND a.shared_type= %s LIMIT 1
                    """, [shared['id'], int(current_user.id), shared['shared_type']])

            data = cursor.fetchone()
            return send_file( io.BytesIO(data['data'])
                            , mimetype = data['mime']
                            , as_attachment = True
                            , attachment_filename = '%s.%s' % (shared['file_uid'], '')
                            )

        except Warning:
            g.db.rollback()

    abort(500)

@shared.route("/download/public/<uid>", methods = ["GET", "POST"])
def download_public(uid):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                SELECT a.uid AS uid, b.data_mime AS data_mime, b.oid AS oid FROM minicloud_shared AS a
                LEFT JOIN minicloud_files AS b ON (a.file_id = b.id)
                WHERE a.uid = %s AND a.shared_type= %s LIMIT 1
                """, [uid, SHARED_PUBLIC])

            data = cursor.fetchone()
            lobj = g.db.lobject(int(data['oid']), 'rb')
            f = lobj.read()

            suffix = MIME_SUFFIX[data['data_mime']] if data['data_mime'] in MIME_SUFFIX else 'unknwon'
            
            return send_file( io.BytesIO(f)
                            , mimetype = suffix
                            , as_attachment = True
                            , attachment_filename = '%s.%s' % (data['uid'], suffix)
                            )
        except Warning:
            g.db.rollback()

    abort(500)

@shared.route("/download/<uid>", methods = ["GET", "POST"])
@login_required
def download(uid):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                SELECT * FROM minicloud_shared
                WHERE uid = %s LIMIT 1;
                """, [uid])
        
            shared = cursor.fetchone()
            # shared with a single user
            if shared['shared_type'] == SHARED_USER:
                if int(current_user.id) == shared['shared_id']:
                    return download_file(shared['user_id'], shared['file_uid'], uid)

            # shared with the cloud
            if shared['shared_type'] == SHARED_CLOUD:
                return download_file(shared['user_id'], shared['file_uid'], uid)
                
        except Warning:
            g.db.rollback()

    abort(500)

@shared.route("/stream/<uid>", methods = ["GET", "POST"])
@login_required
def stream(uid):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                SELECT * FROM minicloud_shared
                WHERE uid = %s LIMIT 1;
                """, [uid])
        
            shared = cursor.fetchone()
            # shared with a single user
            if shared['shared_type'] == SHARED_USER:
                if int(current_user.id) == shared['shared_id']:
                    return stream_file(shared['user_id'], shared['file_uid'], uid)

            # shared with the cloud
            if shared['shared_type'] == SHARED_CLOUD:
                return stream_file(shared['user_id'], shared['file_uid'], uid)
                
        except Warning:
            g.db.rollback()

    abort(500)
