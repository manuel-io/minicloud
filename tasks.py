import psycopg2, psycopg2.extras, re
from datetime import datetime
from dateutil import tz, parser
from flask import Blueprint, g, request, render_template, url_for, redirect, flash
from users import login_required, admin_required, current_user
from config import config
from helpers import get_categories

tasks = Blueprint('tasks', __name__)

@tasks.route('/')
@login_required
def show():
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        utc = config['general']['utczone']
        dbzone = config['general']['dbzone']
        zone = config['general']['zone']
        today = config['general']['today']
        week = config['general']['week']

        try:
            cursor.execute("""
              SELECT q.category AS name, json_agg(json_build_object('id', id, 'uid', uid, 'status', status, 'title', title, 'due', due, 'done', done, 'process', process)) AS tasks FROM
                (SELECT a.id, a.status, uid, category, title, due, done, process,
                  CASE
                    WHEN a.due IS NULL THEN false
                    ELSE true
                  END AS prefer
                FROM minicloud_tasks AS a
                  JOIN (
                    VALUES ('processing', 1), ('pending', 2), ('completed', 3), ('deleted', 4)
                  ) AS b (status, id) ON (a.status = b.status)
                WHERE user_id = %s ORDER BY category DESC, prefer DESC, b.id ASC, a.created_at DESC
              ) AS q GROUP BY name ORDER BY name DESC
            """, [int(current_user.id)])

            print('>>>>', current_user.id)
            tasks = cursor.fetchall()

            def fmt(task):
                if task['process']:
                    task['process'] = parser.parse(task['process']).replace(tzinfo = dbzone).astimezone(zone).strftime("%-d %b %Y")

                if task['done']:
                    task['done'] = parser.parse(task['done']).replace(tzinfo = dbzone).astimezone(zone).strftime("%-d %b %Y")

                if task['due']:
                    delta = parser.parse(task['due']).replace(tzinfo = dbzone).astimezone(zone) - today
                    task['deadline'] = round(delta.total_seconds()/86400)
                    task['delayed'] = True if task['deadline'] < 0 else False
                    task['due'] = parser.parse(task['due']).replace(tzinfo = dbzone).astimezone(zone).strftime("%-d %b %Y")

                return task

            tasks = [{ 'name': category['name']
                     , 'tasks': list(map(lambda task: fmt(dict(task)), category['tasks']))
                     } for category in tasks]

            return render_template( "tasks/show.html"
                                  , tasks = tasks
                                  , categories = get_categories()
                                  , today = today.strftime('%-d %b %Y')
                                  , week = week
                                  )

        except Exception as e:
            g.db.rollback()
            # Log message e

    abort(500)

@tasks.route("/add", methods = ["POST"])
@login_required
def add():
    week = config['general']['week']
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        title = request.form['title']
        category = request.form['category']
        zone = config['general']['zone'] #tz.gettz('Europa/Berlin')
        deadline = request.form.get('due')
        description = request.form.get('description')
        due = None

        if re.match(r'^\d{4}-\d{2}-\d{2}', deadline):
            due = parser.parse(deadline).replace(tzinfo = zone)

        try:
            cursor.execute("""
                INSERT INTO minicloud_tasks
                (user_id, title, category) VALUES (%s, %s, %s)
                RETURNING id
                """, [ int(current_user.id)
                     , title
                     , category
                     ])

            index = cursor.fetchone()['id']

            if due:
                cursor.execute("""
                    UPDATE minicloud_tasks SET
                    due = %s WHERE id = %s AND user_id = %s
                    """, [due, index, int(current_user.id)])

            if description:
                cursor.execute("""
                    UPDATE minicloud_tasks SET
                    description = %s WHERE id = %s AND user_id = %s
                    """, [description, index, int(current_user.id)])

            g.db.commit()
            flash(['Task added'], 'info')

        except Exception as e:
            g.db.rollback()
            flash(['Failed :-('], 'error')
            # Log message e

    return redirect(url_for('tasks.show'))

@tasks.route("/edit/<uid>", methods = ["GET", "POST"])
@login_required
def edit(uid):
    utc = config['general']['utczone']
    dbzone = config['general']['dbzone']
    zone = config['general']['zone']

    if request.method == "GET":
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT * FROM minicloud_tasks
              WHERE uid = %s AND user_id = %s LIMIT 1;
            """, [uid, int(current_user.id)])

            task = dict(cursor.fetchone())
            for status in config['tasks']['states']:
                if status == task['status']:
                    task['task_status'] = status

                    if status == 'processing':
                        task['task_datetime'] = task['process']

                    if status in ['completed', 'deleted']:
                        task['task_datetime'] = task['done']

            if task['due']:
                task['due'] = task['due'].replace(tzinfo = dbzone).astimezone(zone).strftime('%Y-%m-%d')

        return render_template( "tasks/edit.html"
                               , config = config
                               , task = task
                               , categories = get_categories()
                               )

    if request.method == "POST":
       
        category = request.form['category']
        status = request.form['status']
        old_status = request.form['task_status']
        old_datetime = request.form['task_datetime']
        title = request.form['title']
        deadline = request.form.get('due')
        description = request.form.get('description')
        process, due, done = None, None, None

        if status == old_status:
            process = old_datetime if status == 'processing' else None
            done = old_datetime if status in ['completed', 'deleted'] else None
            if status in ['completed', 'deleted']: deadline = ''

        else:
            if status in ['completed', 'deleted']:
                done = datetime.utcnow().replace(tzinfo = utc)
                deadline = ''

            if status in ['processing']:
                process = datetime.utcnow().replace(tzinfo = utc)

        if re.match(r'^\d{4}-\d{2}-\d{2}', deadline):
            due = parser.parse(deadline).replace(tzinfo = zone)
            
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            try:
                cursor.execute("""
                  UPDATE minicloud_tasks SET
                    status = %s, title = %s, category = %s, description = %s, due = %s, done = %s, process = %s
                  WHERE uid = %s AND user_id = %s
                """, [ status
                     , title
                     , category
                     , description
                     , due
                     , done
                     , process
                     , uid
                     , int(current_user.id)
                     ])

                g.db.commit()
                flash(['Task modified'], 'info')
            
            except Exception as e:
                g.db.rollback();
                flash(['Failed :-('], 'error')
                # Log message e
        
        return redirect(url_for('tasks.show'))

@tasks.route("/delete/<uid>", methods = ["POST"])
@login_required
def delete(uid):
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        try:
            cursor.execute("""
              DELETE FROM minicloud_tasks
              WHERE user_id = %s and uid = %s
            """, [int(current_user.id), uid])

            g.db.commit()
            flash(['Task removed'], 'info')

        except Exception as e:
            g.db.rollback()
            flash(['Failed :-('], 'error')
            # Log message e

    return redirect(url_for('tasks.show'))
