import psycopg2, psycopg2.extras, bcrypt, random, string
from flask import Blueprint, url_for, request, redirect, g, render_template, flash, make_response, jsonify, abort
from flask_login import UserMixin, login_required, current_user
from functools import wraps, reduce
from config import app
from auths import generate, revoke

users = Blueprint('users', __name__)

class User(UserMixin):
    def __init__(self, index, name, admin):
        self.id = index
        self.name = name
        self.admin = admin

    def __repr__(self):
        return "%s" % (self.id)

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
                return redirect(url_for("index"))
        else:
            return redirect(url_for("login"))

    return decorated_view

@users.route("/")
@login_required
@admin_required
def show():
    data = []

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT a.id, uuid, name, email, admin, disabled, count(DISTINCT b.id) AS uploads_count, count(DISTINCT c.id) AS gallery_count, count(DISTINCT d.id) AS tasks_count
              FROM minicloud_users AS a
                LEFT JOIN minicloud_uploads AS b ON (a.id = b.user_id AND b.type = 1)
                LEFT JOIN minicloud_gallery AS c ON (a.id = c.user_id)
                LEFT JOIN minicloud_tasks AS d ON (a.id = d.user_id)
              GROUP BY a.id ORDER BY name ASC;
              """)

            data = cursor.fetchall()
        return render_template("users/show.html", users = data)

    except Exception as e:
        g.db.rollback()
        app.logger.error('Show in users failed: %s' % str(e))

    abort(500)

@users.route("/edit/<uuid>", methods = ["GET", "POST"])
@login_required
@admin_required
def edit(uuid):
    data = []

    if request.method == "GET":
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:

            cursor.execute("""
              SELECT * FROM minicloud_users
              WHERE uuid = %s LIMIT 1;
              """, [ uuid ])

            data = cursor.fetchone()
        return render_template("users/edit.html", user = data)

    if request.method == "POST":
        values = list(map(lambda x: request.form[x], ["username", "email"]))
        admin = True if request.form.get("admin") else False
        disabled = True if request.form.get("disabled") else False

        try:
            with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                  UPDATE minicloud_users
                  SET name = %s, email = %s, admin = %s, disabled = %s
                  WHERE uuid = %s RETURNING id
                  """, values + [admin, disabled, uuid])

                data = cursor.fetchone()

            revoke(data['id'])
            g.db.commit()

            flash(['User modified'], 'info')

        except Exception as e:
            g.db.rollback()
            app.logger.error('Edit in users failed: %s' % str(e))
            flash(['Edit failed'], 'error')

        return redirect("/users")

    abort(501)

@users.route("/add", methods = ["POST"])
@login_required
@admin_required
def add():
    values = list(map(lambda x: request.form[x], ["username", "email"]))
    admin = True if request.form.get("admin") else False
    key = reduce(lambda x, _: x + random.choice(string.ascii_letters + string.digits), range(32), "")
    password = reduce(lambda x, _: x + random.choice(string.ascii_letters + string.digits), range(32), "")

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              INSERT INTO minicloud_users
              (name, email, password, admin, activation_key, disabled)
              VALUES (%s, %s, %s, %s, %s, %s)
              """, values + [password, admin, key, True])

        g.db.commit()
        flash(['User added', 'Activation Key:', key], 'info')

    except Exception as e:
        g.db.rollback()
        app.logger.error('Adding in users failed: %s' % str(e))
        flash(['Adding failed'], 'error')

    return redirect(url_for('users.show'))

@users.route("/delete/<uuid>", methods = ["POST"])
@login_required
@admin_required
def delete(uuid):
    data = []

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              DELETE FROM minicloud_users
              WHERE uuid = %s RETURNING id
              """, [ uuid ])

            data = cursor.fetchone()

        revoke(data['id'])
        g.db.commit()
        flash(['User deleted'], 'info')

    except Exception as e:
        g.db.rollback()
        app.logger.error('Deletion in users failed: %s' % str(e))
        flash(['Deletion failed'], 'error')

    return redirect(url_for('users.show'))

@users.route("/reset/<uuid>", methods = ["POST"])
@login_required
@admin_required
def reset(uuid):
    data = []
    key = reduce(lambda x, _: x + random.choice(string.ascii_letters + string.digits), range(32), "")

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              UPDATE minicloud_users SET activation_key = %s, disabled = %s
              WHERE uuid = %s RETURNING id
              """, [ key, True, uuid ])

            data = cursor.fetchone()

        revoke(data['id'])
        g.db.commit()
        flash(['Activation code:', key], 'info')

    except Exception as e:
        g.db.rollback()
        app.logger.error('Reset in users failed: %s' % str(e))
        flash(['Reset failed'], 'error')

    return redirect(url_for('users.show'))

@users.route("/set_media/", methods = ["POST"])
@login_required
def set_media():
    # generate(current_user.id)
    media = request.form['media']

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              UPDATE minicloud_users
              SET media = %s WHERE id = %s;
              """, [ media, int(current_user.id) ])

        g.db.commit()
        return make_response(jsonify(['Saved']), 200)

    except Exception as e:
        g.db.rollback()
        app.logger.error('Save media failed: %s' % str(e))

    return make_response(jsonify(['Error']), 500)
