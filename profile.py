import psycopg2, psycopg2.extras, json, io, base64
from psycopg2.errors import UniqueViolation
from dateutil import tz, parser
from flask import Blueprint, g, request, render_template, url_for, redirect, flash, send_file, abort
from users import User, login_required, current_user
from config import app, Config
from gallery import pillow_orientation, pillow_thumbnail

profile = Blueprint('profile', __name__)

@profile.route('/', methods = ['GET', 'POST'])
@login_required
def show():
    if request.method == 'GET':
        try:
            with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM minicloud_users
                    WHERE id = %s LIMIT 1;
                    """, [int(current_user.id)])

                user = cursor.fetchone()
                return render_template('profile/show.html', user = user)

        except Exception as e:
            g.db.rollback()
            app.logger.error('Show in profile failed: %s' % str(e))
            flash(['Something went wrong!'], 'error')

        # Redirect to default
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']

        # TODO: Pre check if name is unique
        # TODO: Pre check if email is unique

        try:
            with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                    UPDATE minicloud_users
                    SET name = %s, email = %s WHERE id = %s;
                    """, [name, email, int(current_user.id)])

                g.db.commit()
                flash(['Profile updated'], 'info')

        except Exception as e:
            g.db.rollback()
            app.logger.error('Update in profile failed: %s' % str(e))
            flash(['Update failed'], 'error')

        return redirect(url_for('profile.show'))

    abort(501)

@profile.route('/password', methods = ['POST'])
@login_required
def password():
    password = request.form['password']
    confirmation = request.form['confirmation']

    try:
        if len(password) < 6:
            flash(['Passsword required at least 6 characters'], 'error')
            raise Exception('Passsword required at least 6 characters')

        if not password == confirmation:
            flash(['Confirmation of the password failed'], 'error')
            raise Exception('Confirmation of the password failed')

    except Exception as e:
        app.logger.info('Password format failed: %s' % str(e))
        return redirect(url_for('profile.show'))

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
                UPDATE minicloud_users
                SET password = %s WHERE id = %s;
                """, [User.generate_password(password), int(current_user.id)])

            g.db.commit()
            flash(['Password updated'], 'info')

    except Exception as e:
        g.db.rollback()
        app.logger.error('Password update in profile failed: %s' % str(e))
        flash(['Password not updated'], 'error')

    return redirect(url_for('profile.show'))
