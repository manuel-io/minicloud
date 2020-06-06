#!/usr/bin/python

import psycopg2, psycopg2.extras, bcrypt, io, os
from flask import Flask, flash, g, render_template, request, url_for, redirect
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, current_user
from contextlib import closing
from config import get_db, SECRET_KEY
from users import User, users, login_required
from files import files
from tasks import tasks
from profile import profile
from shared import shared
from tools import tools

app = Flask(__name__)
app.register_blueprint(users, url_prefix='/users')
app.register_blueprint(files, url_prefix='/files')
app.register_blueprint(tasks, url_prefix='/tasks')
app.register_blueprint(profile, url_prefix='/profile')
app.register_blueprint(shared, url_prefix='/shared')
app.register_blueprint(tools, url_prefix='/tools')

@app.teardown_appcontext
def close_db(e = None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

login_manager = LoginManager()
app.config['SECRET_KEY'] = SECRET_KEY
csrf = CSRFProtect(app)
csrf.init_app(app)
login_manager.init_app(app)

@app.before_request
def before_request():
    g.db = get_db();

# handle login failed
@app.errorhandler(401)
def page_not_found(e):
    return redirect(url_for('login'))

# somewhre for activation
@app.route('/login/activation', methods=['GET', 'POST'])
def activation():
    if request.method == 'GET':
        return render_template('activation.html')

    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        confirmation = request.form['confirmation']
        activation = request.form['activation']
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
                    SELECT id, name, activation_key FROM minicloud_users
                    WHERE name = %s AND activation_key = %s AND disabled = %s
                    ORDER BY id ASC LIMIT 1
                    """, [name, activation, True])

                data = cursor.fetchone()
                print('data', data)

            except:
                pass

            try:
                cursor.execute("""
                    UPDATE minicloud_users
                    SET password = %s, activation_key = %s, disabled = %s
                    WHERE id = %s
                    """, [hashed, '0', False, int(data['id'])])

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
        return render_template('login.html')
  
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
    
        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        
            try:
                cursor.execute("""
                    SELECT id, name, password, admin FROM minicloud_users
                    WHERE name = %s AND disabled = %s ORDER BY id ASC LIMIT 1;
                    """, [username, False])
                    
                data = cursor.fetchone()

            except:
                g.db.rollback()

            try:
                user = User(int(data['id']), data['name'], data['admin'])
                if User.check_password(password, data['password']):
                    login_user(user)
                    flash(['Logged in'], 'info')

                else:
                    raise ValueError

            except:
                flash(['Invalid credentials'], 'error')

        if current_user:
            return redirect(url_for('index'))
        
        return render_template('login.html')

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
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:

        cursor.execute("""
            SELECT id, name, admin, disabled FROM minicloud_users
            WHERE id = %s ORDER BY id ASC LIMIT 1;
            """, [int(id)])
        
        data = cursor.fetchone()
        return User(int(data['id']), data['name'], data['admin'])

@app.route('/')
@login_required
def index():
    return redirect(url_for('files.show'))

if __name__ == '__main__':
    app.run(host = '127.0.0.1')
