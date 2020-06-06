import psycopg2, psycopg2.extras, bcrypt, random, string
from flask import Blueprint, url_for, request, redirect, g, render_template, flash
from flask_login import UserMixin, login_required, current_user
from contextlib import closing
from functools import wraps, reduce
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
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:

        cursor.execute("""
            SELECT a.id, name, email, admin, disabled, count(DISTINCT b.id) AS file_count, count(DISTINCT c.id) AS task_count
            FROM minicloud_users AS a
            LEFT JOIN minicloud_files AS b ON (a.id = b.user_id)
            LEFT JOIN minicloud_tasks AS c ON (a.id = c.user_id)
            GROUP BY a.id ORDER BY name ASC;
            """)

        users = cursor.fetchall()

    return render_template("users/show.html", users = users)

@users.route("/edit/<int:index>", methods = ["GET", "POST"])
@login_required
@admin_required
def edit_user(index):
    if request.method == "GET":
        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:

            cursor.execute("""
                SELECT * FROM minicloud_users
                WHERE id = %s LIMIT 1;
                """, [index])

            data = cursor.fetchone()
            return render_template("users/edit.html", user = data)

    if request.method == "POST":
        values = list(map(lambda x: request.form[x], ["name", "email"]))
        admin = True if request.form.get("admin") else False
        disabled = True if request.form.get("disabled") else False
       
        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
            try:
                cursor.execute("""
                    UPDATE minicloud_users
                    SET name = %s, email = %s, admin = %s, disabled = %s
                    WHERE id = %s;
                    """, values + [admin, disabled, index])

                g.db.commit()
                flash(['User modified'], 'info')

            except Warning:
                g.db.rollback()

            return redirect("/users")

@users.route("/add", methods = ["POST"])
@login_required
@admin_required
def add_user():
    name = request.form['name']
    email = request.form['email']
    #password = request.form['password']
    #password_validation = request.form['password_validation']
    admin = True if request.form.get("admin") else False
    key = reduce(lambda x, _: x + random.choice(string.ascii_letters + string.digits), range(32), "")
    password = reduce(lambda x, _: x + random.choice(string.ascii_letters + string.digits), range(32), "")

    #if len(password) > 4:
    #    if password == password_validation:
    #        hash = bcrypt.hashpw(password, bcrypt.gensalt())

    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                INSERT INTO minicloud_users
                (name, email, password, admin, activation_key, disabled)
                VALUES (%s, %s, %s, %s, %s, %s)
                """, [name, email, password, admin, key, True])
            
            g.db.commit()

        except:
            g.db.rollback()

    #g.alerts = [ { 'info': ['Activation Key', key] }]

    flash(['User added'], 'info')
    flash(['Activation Key:', key], 'alert')

    return redirect("/users")

@users.route("/delete/<int:index>", methods = ["POST"])
@login_required
@admin_required
def delete_user(index):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                DELETE FROM minicloud_users
                WHERE id = %s;
                """, [index])

            g.db.commit()
            flash(['User removed'], 'info')

        except Warning:
            g.db.rollback()

    return redirect("/users")

@users.route("/reset/<int:index>", methods = ["POST"])
@login_required
@admin_required
def reset_user(index):
    key = reduce(lambda x, _: x + random.choice(string.ascii_letters + string.digits), range(32), "")
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                UPDATE minicloud_users
                SET activation_key = %s, disabled = %s
                WHERE id = %s;
                """, [key, True, index])

            g.db.commit()
            flash(['Activation Key:', key], 'alert')

        except Warning:
            g.db.rollback()

    return redirect("/users")
