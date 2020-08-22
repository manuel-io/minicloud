import psycopg2, psycopg2.extras, re
from datetime import datetime
from dateutil import tz, parser
from flask import Blueprint, g, request, render_template, url_for, redirect, flash, abort
from users import login_required, admin_required, current_user
from config import app, config
from helpers import get_categories, format_task

tasks = Blueprint('tasks', __name__)

@tasks.route('/')
@login_required
def show():
    ref = 'pending'
    today = config['general']['today']
    week = config['general']['week']
    tasks = []

    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT category AS name, json_agg(json_build_object('id', id, 'uid', uid, 'status', status, 'title', title, 'due', due, 'done', done, 'process', process) ORDER BY created_at ASC) AS tasks
              FROM minicloud_tasks WHERE user_id = %s AND ARRAY[status] @> %s
              GROUP BY category ORDER BY category ASC;
            """, [int(current_user.id), [ref]])

            tasks = cursor.fetchall()

    except Exception as e:
        app.logger.error('Show in tasks failed: %s' % str(e))
        g.db.rollback()

    tasks = [{ 'name': category['name']
             , 'tasks': [format_task(dict(task)) for task in category['tasks']]
             } for category in tasks]

    return render_template( 'tasks/show.html'
                          , tasks = tasks
                          , categories = get_categories()
                          , today = today.strftime('%-d %b %Y')
                          , week = week
                          , ref = ref
                          )

@tasks.route('/add', methods = ['POST'])
@login_required
def add():
    zone = config['general']['zone']
    title = request.form['title']
    category = request.form['category']
    deadline = request.form['deadline']
    description = request.form['description']
    due = None

    if re.match(r'^\d{4}-\d{2}-\d{2}', deadline):
        due = parser.parse(deadline).replace(tzinfo = zone)

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              INSERT INTO minicloud_tasks (user_id, title, category, description)
              VALUES (%s, %s, %s, %s)
              RETURNING id
              """, [int(current_user.id), title, category, description])

            index = cursor.fetchone()['id']

            if due:
                cursor.execute("""
                  UPDATE minicloud_tasks
                  SET due = %s WHERE id = %s AND user_id = %s
                  """, [due, index, int(current_user.id)])

        g.db.commit()
        flash(['Task added'], 'info')

    except Exception as e:
        app.logger.error('Adding in tasks failed: %s' % str(e))
        g.db.rollback()
        flash(['Adding failed'], 'error')

    return redirect(url_for('tasks.show'))

@tasks.route("/edit/<uid>", methods = ["GET", "POST"])
@login_required
def edit(uid):
    ref = 'pending'
    utc = config['general']['utczone']
    dbzone = config['general']['dbzone']
    zone = config['general']['zone']
    task = None

    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT * FROM minicloud_tasks
              WHERE uid = %s AND user_id = %s LIMIT 1;
              """, [uid, int(current_user.id)])

            task = dict(cursor.fetchone())

        if not task:
            raise Exception('Task not found')

    except Exception as e:
        app.logger.error('Edit failed: %s' % str(e))
        g.db.rollback();
        flash(['Edit failed'], 'error')
        return redirect(url_for('tasks.show', ref = ref))

    if request.method == 'GET':
        if task['due']:
            task['deadline'] = task['due'].replace(tzinfo = dbzone).astimezone(zone).strftime('%Y-%m-%d')

        return render_template( 'tasks/edit.html'
                               , config = config
                               , task = task
                               , categories = get_categories()
                               , ref = ref
                               )

    if request.method == 'POST':
        category = request.form['category']
        status = request.form['status']
        title = request.form['title']
        deadline = request.form['deadline']
        description = request.form['description']
        process, due, done = None, None, None

        if re.match(r'^\d{4}-\d{2}-\d{2}', deadline):
            due = parser.parse(deadline).replace(tzinfo = zone)

        try:
            with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                  UPDATE minicloud_tasks
                  SET title = %s, category = %s, description = %s, due = %s
                  WHERE uid = %s AND user_id = %s
                  """, [title, category, description, due, uid, int(current_user.id)])

                if not status == task['status']:
                    ref = status

                    if status in ['completed', 'deleted']:
                        done = datetime.utcnow().replace(tzinfo = utc)
                        process = None
                        deadline = None
                        due = None

                    if status in ['processing']:
                        process = datetime.utcnow().replace(tzinfo = utc)
                        done = None

                    if status in ['pending']:
                        done = None
                        process = None

                    cursor.execute("""
                      UPDATE minicloud_tasks
                      SET status = %s, due = %s, done = %s, process = %s
                      WHERE uid = %s AND user_id = %s
                      """, [status, due, done, process, uid, int(current_user.id)])

            g.db.commit()
            flash(['Task modified'], 'info')

        except Exception as e:
            app.logger.error('Edit in tasks failed: %s' % str(e))
            g.db.rollback();
            flash(['Edit failed'], 'error')

        return redirect(url_for('tasks.show', ref = ref))

    abort(501)

@tasks.route("/delete/<uid>", methods = ["POST"])
@login_required
def delete(uid):
    ref = 'panding'
    if 'ref' in request.args.keys():
        ref = request.args.get('ref').strip()

    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              DELETE FROM minicloud_tasks
              WHERE user_id = %s and uid = %s
              """, [int(current_user.id), uid])

            g.db.commit()
            flash(['Task removed'], 'info')

    except Exception as e:
        app.logger.error('Deletion in tasks failed: %s' % str(e))
        g.db.rollback()
        flash(['Deletion failed'], 'error')

    return redirect(url_for('tasks.show', ref = ref))
