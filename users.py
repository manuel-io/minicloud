import psycopg2, psycopg2.extras, bcrypt, random, string
from flask import Blueprint, url_for, request, redirect, g, render_template, flash, make_response, jsonify, abort
from flask_login import UserMixin, login_required, current_user
from functools import wraps, reduce
from config import app, Config
from auths import generate, revoke
from helpers import format_registered

users = Blueprint('users', __name__)

class User(UserMixin):
    def __init__(self, index, name, admin):
        self.id = index
        self.name = name
        self.admin = admin

    def __repr__(self):
        return '%s' % (self.id)

    @staticmethod
    def generate_password(pwd):
        return bcrypt.hashpw(pwd, bcrypt.gensalt())

    @staticmethod
    def check_password(pwd, hash):
        return bcrypt.checkpw(pwd, hash)

def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_user.is_authenticated:
            if current_user.admin:
                return func(*args, **kwargs)
            else:
                return redirect(url_for('index'))
        else:
            return redirect(url_for('login'))

    return decorated_view

@users.route('/')
@login_required
@admin_required
def show():
    ref = 'users'

    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    case = True if ref == 'admins' else False

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
            SELECT a.id, uuid, name, email, admin, disabled, count(DISTINCT b.id) AS uploads_count, count(DISTINCT c.id) AS gallery_count, count(DISTINCT d.id) AS tasks_count, a.activation_key, a.created_at
            FROM minicloud_users AS a
            LEFT JOIN minicloud_uploads AS b ON (a.id = b.user_id AND b.type = 1)
            LEFT JOIN minicloud_gallery AS c ON (a.id = c.user_id)
            LEFT JOIN minicloud_tasks AS d ON (a.id = d.user_id)
            WHERE a.admin = %s GROUP BY a.id ORDER BY name ASC;
            """, [case])

            users = [ format_registered(dict(user)) for user in cursor.fetchall() ]
            return render_template('users/show.html', users = users, ref = ref)

    except Exception as e:
        app.logger.error('Show in users failed: %s' % str(e))
        flash(['Something went wrong!'], 'error')

    # Redirect to default
    return redirect(url_for('index'))

@users.route('/edit/<uuid>', methods = ['GET', 'POST'])
@login_required
@admin_required
def edit(uuid):
    ref = 'users'

    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    if request.method == 'GET':
        try:
            with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                SELECT * FROM minicloud_users
                WHERE uuid = %s LIMIT 1;
                """, [ uuid ])

                user = cursor.fetchone()
                return render_template("users/edit.html", user = user, ref = ref)

        except Exception as e:
            app.logger.error('Edit in users failed: %s' % str(e))
            flash(['Something went wrong!'], 'error')
            return redirect(url_for('users.show'))

    if request.method == 'POST':
        name = request.form['username']
        email = request.form['email']
        admin = True if request.form.get('admin') else False
        disabled = True if request.form.get('disabled') else False

        ref = 'admins' if admin else 'users';

        # TODO: Pre check if name is unique
        # TODO: Pre check if email is unique

        try:
            with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                UPDATE minicloud_users
                SET name = %s, email = %s, admin = %s, disabled = %s
                WHERE uuid = %s RETURNING id
                """, [name, email, admin, disabled, uuid])

                user = cursor.fetchone()
                g.db.commit()
                revoke(user['id'])
                flash(['User modified'], 'info')
                return redirect(url_for('users.edit', uuid = uuid, ref = ref))

        except Exception as e:
            g.db.rollback()
            app.logger.error('Edit in users failed: %s' % str(e))
            flash(['Edit failed'], 'error')

        return redirect(url_for('users.show', ref = ref))

    abort(501)

@users.route('/add', methods = ['POST'])
@login_required
@admin_required
def add():
    name = request.form['username']
    email = request.form['email']
    admin = True if request.form.get("admin") else False
    key = reduce(lambda x, _: x + random.choice(string.ascii_letters + string.digits), range(32), '')
    password = reduce(lambda x, _: x + random.choice(string.ascii_letters + string.digits), range(32), '')

    ref = 'admins' if admin else 'users';

    # TODO: Pre check if name is unique
    # TODO: Pre check if email is unique

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
            INSERT INTO minicloud_users
            (name, email, password, admin, activation_key, disabled)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING uuid
            """, [name, email, password, admin, key, True])

            user = cursor.fetchone()
            g.db.commit()
            flash(['User added'], 'info')
            return redirect(url_for('users.edit', uuid = user['uuid'], ref = ref))

    except Exception as e:
        g.db.rollback()
        app.logger.error('Adding in users failed: %s' % str(e))
        flash(['Adding failed'], 'error')

    return redirect(url_for('users.show', ref = ref))

@users.route("/delete/<uuid>", methods = ["POST"])
@login_required
@admin_required
def delete(uuid):
    ref = 'users'

    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
            DELETE FROM minicloud_users
            WHERE uuid = %s
            """, [uuid])

            g.db.commit()
            flash(['User deleted'], 'info')

    except Exception as e:
        g.db.rollback()
        app.logger.error('Deletion in users failed: %s' % str(e))
        flash(['Deletion failed'], 'error')

    return redirect(url_for('users.show', ref = ref))

@users.route('/reset/<uuid>', methods = ['POST'])
@login_required
@admin_required
def reset(uuid):
    ref = 'users'

    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    key = reduce(lambda x, _: x + random.choice(string.ascii_letters + string.digits), range(32), '')

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
            UPDATE minicloud_users SET activation_key = %s, disabled = %s
            WHERE uuid = %s RETURNING id
            """, [key, True, uuid])

            user = cursor.fetchone()
            g.db.commit()
            revoke(user['id'])
            flash(['User reseted'], 'info')
            return redirect(url_for('users.edit', uuid = uuid, ref = ref))

    except Exception as e:
        g.db.rollback()
        app.logger.error('Reset in users failed: %s' % str(e))
        flash(['Reset failed'], 'error')

    return redirect(url_for('users.show'))

@users.route('/set_media/<uuid>', methods = ['GET'])
@login_required
def set_media(uuid):
    media = request.args['media']

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
            UPDATE minicloud_users
            SET media = %s WHERE id = %s;
            """, [media, current_user.id])

        g.db.commit()
        return make_response(jsonify(['Saved']), 200)

    except Exception as e:
        g.db.rollback()
        app.logger.error('Save media failed: %s' % str(e))

    return make_response(jsonify([]), 500)
