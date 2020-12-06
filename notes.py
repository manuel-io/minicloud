import psycopg2, psycopg2.extras, sys, os
from datetime import datetime
from flask import Blueprint, g, request, render_template, url_for, redirect, flash, abort, make_response, jsonify
from users import User, login_required, current_user
from config import app, Config
from helpers import get_categories

notes = Blueprint('notes', __name__)

@notes.route('/', methods = ['GET'])
@login_required
def show():
    utc = Config.UTCZONE
    zone = Config.ZONE
    today = datetime.utcnow().replace(tzinfo=utc).astimezone(zone).strftime('%-d. %B %Y, %H:%M')
    last = datetime.utcnow().replace(tzinfo=utc)
    uid = None
    previous = None
    forward = None
    text = ''
    category = 'Default'
    tags = []

    if 'uid' in request.args.keys():
        uid = request.args.get('uid')

    try:
        if uid:
            with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                SELECT * FROM minicloud_notes WHERE user_id = %s AND uid = %s
                """, [current_user.id, uid])

                note = cursor.fetchone()
                if note:
                    last = note['created_at']
                    today = last.replace(tzinfo=utc).astimezone(zone).strftime('%-d. %B %Y, %H:%M')
                    uid = note['uid']
                    text = note['description']
                    category = note['category']
                    tags = note['tags']

        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
            SELECT * FROM minicloud_notes WHERE user_id = %s
            AND created_at < %s ORDER BY created_at DESC LIMIT 1
            """, [current_user.id, last])

            data1 = cursor.fetchone()
            if data1: previous = data1['uid']

        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
            SELECT * FROM minicloud_notes WHERE user_id = %s
            AND created_at > %s ORDER BY created_at ASC LIMIT 1
            """, [current_user.id, last])

            data2 = cursor.fetchone()
            if data2: forward = data2['uid']

    except Exception as e:
        app.logger.error('Show in notes failed: %s' % str(e))
        flash(['Show failed'], 'error')

    return render_template('notes/show.html'
                          , today = today
                          , uid = uid
                          , text = text
                          , category = category
                          , categories = get_categories()
                          , tags = tags
                          , previous = previous
                          , forward = forward
                          )

@notes.route('/search', methods = ['POST'])
@login_required
def search():
    utc = Config.UTCZONE
    zone = Config.ZONE
    results = []
    search = request.form['search']
    tags = []
    if 'tags' in request.form.keys():
        tags = [ tag.strip() for tag in request.form.get('tags').split(',') if len(tag.strip()) > 0 ]

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT * FROM minicloud_notes
              WHERE user_id = %s
              AND to_tsvector('simple', description) @@ to_tsquery('simple', %s)
              AND tags @> %s ORDER BY created_at DESC LIMIT 10
              """, [ current_user.id, search, tags ])

            data = cursor.fetchall()
            if data:
                for result in data:
                    xoffset = 20
                    yoffset = 20
                    total = len(result['description'].strip())
                    start = result['description'].strip().find(search)

                    if (start - xoffset) <= 0:
                      xoffset = start

                    if (start + yoffset) >= total:
                      yoffset = (total - start)

                    results.append({ 'uid': result['uid']
                                   , 'today': result['created_at'].replace(tzinfo=utc).astimezone(zone).strftime('%Y-%m-%d, %H:%M')
                                   , 'description': result['description'].strip()[(start - xoffset):(start + yoffset)]
                                   })

    except Exception as e:
        app.logger.error('Search in notes failed: %s' % str(e))

    return make_response(jsonify(results), 200)

@notes.route('/save', methods = ['POST'])
@login_required
def save():
    description = request.form['description']
    category = request.form['category']
    tags = []
    if 'tags' in request.form.keys():
        tags = [ tag.strip() for tag in request.form.get('tags').split(',') if len(tag.strip()) > 0 ]

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
            INSERT INTO minicloud_notes (user_id, description, category, tags)
            VALUES (%s, %s, %s, %s) RETURNING uid
            """, [current_user.id, description, category, tags])

            g.db.commit()
            uid = cursor.fetchone()['uid']
            flash(['Paper saved'], 'info')
            return redirect(url_for('notes.show', uid = uid))

    except Exception as e:
        app.logger.error('Save in notes failed: %s' % str(e))
        flash(['Save failed'], 'error')
        g.db.rollback()

    return redirect(url_for('notes.show'))

@notes.route('/save/<uid>', methods = ['POST'])
@login_required
def edit(uid):
    description = request.form['description']
    category = request.form['category']
    tags = []
    if 'tags' in request.form.keys():
        tags = [ tag.strip() for tag in request.form.get('tags').split(',') if len(tag.strip()) > 0 ]

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
            UPDATE minicloud_notes SET description = %s, category = %s, tags = %s
            WHERE user_id = %s AND uid = %s
            """, [description, category, tags, current_user.id, uid])

            g.db.commit()
            flash(['Paper updated'], 'info')
            return redirect(url_for('notes.show', uid = uid))

    except Exception as e:
        app.logger.error('Save in notes failed: %s' % str(e))
        flash(['Save failed'], 'error')
        g.db.rollback()

    return redirect(url_for('notes.show'))

@notes.route('/delete/<uid>', methods = ['POST'])
@login_required
def delete(uid):
    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              DELETE FROM minicloud_notes WHERE user_id = %s AND uid = %s
              """, [current_user.id, uid])

            g.db.commit()
            flash(['Paper deleted '], 'info')

    except Exception as e:
        app.logger.error('Delete in notes failed: %s' % str(e))
        flash(['Delete failed'], 'error')
        g.db.rollback()

    return redirect(url_for('notes.show'))
