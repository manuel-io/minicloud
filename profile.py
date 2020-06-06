import psycopg2, psycopg2.extras, json, io, base64
from PIL import Image
from psycopg2.errors import UniqueViolation
from datetime import datetime
from dateutil import parser
from flask import Blueprint, g, request, render_template, url_for, redirect, flash, Response
from users import User, login_required, current_user
from contextlib import closing
from config import config
from files import pillow_orientation, pillow_thumbnail

profile = Blueprint('profile', __name__)

@profile.route('/', methods = ["GET", "POST"])
@login_required
def show():
    if request.method == "GET":
        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
            try:
                cursor.execute("""
                    SELECT * FROM minicloud_users
                    WHERE id = %s LIMIT 1;
                    """, [int(current_user.id)])

                user = cursor.fetchone()
                return render_template("profile/show.html", user = user)

            except:
                g.db.rollback()

    if request.method == "POST":
        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
            name = request.form['name']
            email = request.form['email']

            try:
                cursor.execute("""
                    UPDATE minicloud_users
                    SET name = %s, email = %s
                    WHERE id = %s;
                    """, [name, email, int(current_user.id)])

                g.db.commit()
                flash(['Profile updated'], 'info')

            except:
                g.db.rollback()
                flash(['Profile not updated'], 'error')

    return redirect("/profile")

@profile.route("/import", methods = ["POST"])
@login_required
def profile_import():
    dbzone = config['general']['dbzone']
    zone = config['general']['zone']
    f = request.files["file"]
    mimetype = f.content_type

    if mimetype != 'application/json':
        return 'no'
    
    amount = 0
    imported = json.loads(f.read())

    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        if 'files' in imported:
            for file in imported['files']:
                try:
                    upload = base64.b64decode(file['data'].encode())
                    thumbnail_data = None
                    thumbnail_mime = None
                    mimetype = file['data_mime'] if 'data_mime' in file else file['mime']
                    data_size = file['data_size'] if 'data_size' in file else len(upload)
                    description = file['description'] if 'description' in file else ''
                    
                    if mimetype in ["image/jpeg", "image/png"]:
                        upload = pillow_orientation(upload, mimetype)
                        data_size = len(upload)

                    if mimetype in ["image/jpeg", "image/png"]:
                        thumbnail_data = pillow_thumbnail(upload, mimetype)
                        thumbnail_mime = mimetype
    
                    cursor.execute("""
                        INSERT INTO minicloud_files
                        (user_id, uid, category, title, description, data_size, data_mime, thumbnail_mime, thumbnail)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING oid
                        """, ( int(current_user.id)
                             , file['uid']
                             , file['category']
                             , file['title']
                             , description
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
                    amount += 1
    
                except Warning:
                    g.db.rollback()
    
    flash(['%s File%s imported' % (amount, '' if amount == 1 else 's')], 'info')
    amount = 0
              
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        if 'tasks' in imported:
            for task in imported['tasks']:
                try:
                    task['entry'] = parser.parse(task['entry']).astimezone(dbzone)
                    cursor.execute("""
                        INSERT INTO minicloud_tasks
                        (uid, status, entry, category, description, user_id)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                        """, [ task['uid']
                             , task['status']
                             , task['entry']
                             , task['category']
                             , task['description']
                             , int(current_user.id)
                             ])
    
                    data = cursor.fetchone()
                    index = data['id']
    
                    for field in ['annotation']:
                        if task[field]:
                            update = """UPDATE minicloud_tasks SET %s""" % field
                            cursor.execute(update + """
                                = %s WHERE id = %s;
                                """, [task[field], index])
    
                    for field in ['due', 'done', 'process', 'modified']:
                        if task[field]:
                            task[field] = parser.parse(task[field]).astimezone(dbzone)
                            update = """UPDATE minicloud_tasks SET %s""" % field
                            cursor.execute(update + """
                                = %s WHERE id = %s;
                                """, [task[field], index])
    
                    g.db.commit()
                    amount += 1
    
                except UniqueViolation:
                    g.db.rollback()
    
                except:
                    g.db.rollback()

    flash(['%s Task%s imported' % (amount, '' if amount == 1 else 's')], 'info')
    return redirect("/profile")

@profile.route("/export", methods = ["POST"])
@login_required
def profile_export():
    dbzone = config['general']['dbzone']
    zone = config['general']['zone']
    today = config['general']['today']
    now = today.strftime('%Y-%m-%d')

    files = request.form['files']
    exported = {}

    if request.method == "POST":
        if True:
            with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
                try:
                    cursor.execute("""
                        SELECT uid, status, category, description, annotation, entry, due, done, process, modified FROM minicloud_tasks
                        WHERE user_id = %s ORDER BY entry;
                        """, [int(current_user.id)])
                        
                    tasks = cursor.fetchall()
        
                    def fmt(task):
                        if task['process']:
                            task['process'] = task['process'].replace(tzinfo = dbzone).astimezone(zone).isoformat()
            
                        if task['done']:
                            task['done'] =  task['done'].replace(tzinfo = dbzone).astimezone(zone).isoformat()
            
                        if task['due']:
                            task['due'] = task['due'].replace(tzinfo = dbzone).astimezone(zone).isoformat()
                        
                        if task['entry']:
                            task['entry'] = task['entry'].replace(tzinfo = dbzone).astimezone(zone).isoformat()
            
                        if task['modified']:
                            task['modified'] = task['modified'].replace(tzinfo = dbzone).astimezone(zone).isoformat()
            
                        return task
                        
                    exported.update({ 'tasks': list(map(lambda task: fmt(dict(task)), tasks)) })
    
                except Warning:
                    g.db.rollback()

        if files == 'all':
            with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
                try:
                    cursor.execute("""
                        SELECT uid, title, description, category, data_size, data_mime, oid
                        FROM minicloud_files WHERE user_id = %s ORDER BY title;
                        """, [int(current_user.id)])

                    files = cursor.fetchall()
                    
                    def fmt(data):
                        oid = int(data['oid'])
                        lobj = g.db.lobject(oid, 'rb')
                        stream = lobj.read()
                        lobj.close()
                        
                        data['data'] = base64.b64encode(stream).decode()
                        return data
                    
                    exported.update({ 'files': list(map(lambda file: fmt(dict(file)), files)) })

                except Warning:
                    g.db.rollback()

        return Response( json.dumps(exported)
                       , mimetype = 'application/json'
                       , headers = { 'Content-Disposition': 'attachment;filename=minicloud-%s-%s.json' % (current_user.name, now) })

@profile.route("/password", methods = ["POST"])
@login_required
def password():
    password = request.form['password']
    confirmation = request.form['confirmation']
    check = True

    if len(password) < 6:
        flash(['Passsword required at least 6 characters'], 'error')
        check = False if check is True else False

    if not password == confirmation:
        flash(['Password doesn\'t satisfy confirmation'], 'error')
        check = False if check is True else False

    if check:
        hashed = User.generate_password(password)

    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                UPDATE minicloud_users
                SET password = %s WHERE id = %s;
                """, [hashed, int(current_user.id)])

            g.db.commit()
            flash(['Password updated'], 'info')

        except:
          g.db.rollback()
          flash(['Password not updated'], 'error')

    return redirect("/profile")
