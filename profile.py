import psycopg2, psycopg2.extras, json, io, base64
from psycopg2.errors import UniqueViolation
from dateutil import tz, parser
from flask import Blueprint, g, request, render_template, url_for, redirect, flash, send_file, abort
from users import User, login_required, current_user
from config import app, Config
from gallery import pillow_orientation, pillow_thumbnail

profile = Blueprint('profile', __name__)

@profile.route('/', methods = ["GET", "POST"])
@login_required
def show():
    if request.method == "GET":
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            try:
                cursor.execute("""
                    SELECT * FROM minicloud_users
                    WHERE id = %s LIMIT 1;
                    """, [int(current_user.id)])

                user = cursor.fetchone()
                return render_template("profile/show.html", user = user)

            except Exception as e:
                app.logger.error('Show in profile failed: %s' % str(e))
                g.db.rollback()

    if request.method == "POST":
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
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

            except Exception as e:
                app.logger.error('Update in profile failed: %s' % str(e))
                g.db.rollback()
                flash(['Update failed'], 'error')

    abort(501)

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

    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
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
              
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
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
    utczone = config['general']['utczone']
    dbzone = config['general']['dbzone']
    zone = config['general']['zone']
    today = config['general']['today']
    now = today.strftime('%Y-%m-%d')

    version = Config.VERSION
    timestamp = Config.getUnixTimestamp()

    options = request.form.getlist('option')

    exported = { 'version': version
               , 'date': timestamp
               , 'items': {}
               }

    return send_file( io.BytesIO(bytes(json.dumps(exported), encoding = 'utf-8'))
                    , mimetype = 'application/json'
                    , as_attachment = True
                    , attachment_filename = 'minicloud-v%s-%s-%s.json' % (version, current_user.name, timestamp)
                    , cache_timeout = 0
                    )

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

    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
                UPDATE minicloud_users
                SET password = %s WHERE id = %s;
                """, [hashed, int(current_user.id)])

            g.db.commit()
            flash(['Password updated'], 'info')

        except Exception as e:
          app.logger.error('Password update in profile failed: %s' % str(e))
          g.db.rollback()
          flash(['Password not updated'], 'error')

    return redirect(url_for('profile.show'))
