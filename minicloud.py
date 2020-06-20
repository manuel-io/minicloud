#!/usr/bin/python

import psycopg2, psycopg2.extras, bcrypt, io, os, urllib.request
from flask import Flask, flash, g, render_template, request, url_for, redirect
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, current_user
from config import get_db, Config
from users import User, users, login_required
from uploads import uploads
from gallery import gallery
from tasks import tasks
from profile import profile
from multimedia import multimedia

app = Flask(__name__)
app.register_blueprint(users, url_prefix='/users')
app.register_blueprint(uploads, url_prefix='/uploads')
app.register_blueprint(gallery, url_prefix='/gallery')
app.register_blueprint(tasks, url_prefix='/tasks')
app.register_blueprint(profile, url_prefix='/profile')
app.register_blueprint(multimedia, url_prefix='/multimedia')

@app.teardown_appcontext
def close_db(e = None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

login_manager = LoginManager()
app.config['SECRET_KEY'] = Config.SECRET_KEY
csrf = CSRFProtect(app)
csrf.init_app(app)
login_manager.init_app(app)

@app.before_request
def before_request():
    g.db = get_db()

# handle login failed
@app.errorhandler(401)
def page_not_found(e):
    page = url_for(request.endpoint, **request.view_args, _external = True)
    return redirect(url_for('login', page = page))

@app.context_processor
def globals():
    return dict(example = "Hello World")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('users/login.html')

    if request.method == 'POST':
        email = request.form['email']
        code = request.form['code']
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
                    SELECT id, email, activation_key FROM minicloud_users
                    WHERE email = %s AND activation_key = %s AND disabled = %s
                    ORDER BY id ASC LIMIT 1
                    """, [email, code, True])

                data = cursor.fetchone()
                print('data', data)

            except:
                pass

            try:
                cursor.execute("""
                    UPDATE minicloud_users
                    SET password = %s, activation_key = %s, disabled = %s
                    WHERE id = %s
                    """, [hashed, None, False, int(data['id'])])

                g.db.commit()
                flash(['Activation successful'], 'info')

            except:
                g.db.rollback()
                flash(['Activation failed'], 'error')

        return redirect(url_for("index"))

# somewhere to login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        page = request.args.get('page')
        return render_template('users/login.html', page = page)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        page = request.form.get('page')

        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:

            try:
                cursor.execute("""
                    SELECT id, name, password, admin FROM minicloud_users
                    WHERE name = %s AND disabled = %s ORDER BY id ASC LIMIT 1;
                    """, [username, False])

                data = cursor.fetchone()

                user = User(int(data['id']), data['name'], data['admin'])
                if User.check_password(password, data['password']):
                    login_user(user)

            except Exception as e:
                g.db.rollback()

        if current_user.is_authenticated:
            flash(['Logged in'], 'info')

            if page:
                code = urllib.request.urlopen(page).getcode()
                if code > 199 and code < 300:
                    return redirect(page)

            return redirect(url_for('gallery.show'))

        else:
            flash(['Invalid credentials'], 'error')

        return render_template('users/login.html')

# somewhere to logout
@app.route('/logout', methods = ['POST'])
@login_required
def logout():
    logout_user()
    flash(['Logged out'], 'info')
    return redirect(url_for('index'))

# callback to reload the user object
@login_manager.user_loader
def load_user(id):
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:

        cursor.execute("""
            SELECT id, name, admin, disabled FROM minicloud_users
            WHERE id = %s ORDER BY id ASC LIMIT 1;
            """, [int(id)])
        
        data = cursor.fetchone()
        return User(int(data['id']), data['name'], data['admin'])

@app.route('/')
@login_required
def index():
    return redirect(url_for('gallery.show'))

if __name__ == '__main__':
    app.run(host = '127.0.0.1', debug = True)
