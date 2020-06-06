import psycopg2, psycopg2.extras, re
from datetime import datetime
from dateutil import parser
from flask import Blueprint, g, request, render_template, url_for, redirect, flash
from users import login_required, admin_required, current_user
from contextlib import closing
from config import config

tasks = Blueprint('tasks', __name__)

@tasks.route('/')
@login_required
def show():
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        utc = config['general']['utczone']
        dbzone = config['general']['dbzone']
        zone = config['general']['zone']
        today = config['general']['today']
        week = config['general']['week']

        try:
            cursor.execute("""
                SELECT q.category AS name, json_agg(json_build_object('id', id, 'status', status, 'description', description, 'due', due, 'done', done, 'process', process)) AS tasks FROM
                  (SELECT a.id, a.status, category, description, due, done, process,
                    CASE
                      WHEN a.due IS NULL THEN false
                      ELSE true
                    END AS prefer
                  FROM minicloud_tasks AS a
                    JOIN (
                      VALUES ('processing', 1), ('pending', 2), ('completed', 3), ('deleted', 4)
                    ) AS b (status, id) ON (a.status = b.status)
                  ORDER BY category DESC, prefer DESC, b.id ASC, a.entry DESC
             ) AS q GROUP BY category ORDER BY category DESC
                """, [int(current_user.id)])

            categories = cursor.fetchall()

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
             
            categories = [{ 'name': category['name']
                          , 'tasks': list(map(lambda task: fmt(dict(task)), category['tasks']))
                          } for category in categories]

        except Warning:
            g.db.rollback()

    return render_template( "tasks/show.html"
                          , categories = categories
                          , today = today.strftime('%-d %b %Y')
                          , week = week
                          )

@tasks.route("/add", methods = ["POST"])
@login_required
def add():
    week = config['general']['week']
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        description = request.form['description']
        zone = config['general']['zone'] #tz.gettz('Europa/Berlin')
        deadline = request.form.get('due')
        annotation = request.form.get('annotation')
        due = None

        if re.match(r'^\d{4}-\d{2}-\d{2}', deadline):
            due = parser.parse(deadline).replace(tzinfo = zone)

        try:
            cursor.execute("""
                INSERT INTO minicloud_tasks
                (user_id, description, category) VALUES (%s, %s, %s)
                RETURNING id
                """, [ int(current_user.id)
                     , description
                     , 'Week %s' % week
                     ])

            index = cursor.fetchone()['id']

            if due:
                cursor.execute("""
                    UPDATE minicloud_tasks SET
                    due = %s WHERE id = %s AND user_id = %s
                    """, [due, index, int(current_user.id)])

            if annotation:
                cursor.execute("""
                    UPDATE minicloud_tasks SET
                    annotation = %s WHERE id = %s AND user_id = %s
                    """, [annotation, index, int(current_user.id)])

            g.db.commit()
            flash(['Task added'], 'info')

        except Warning:
            g.db.rollback()

    return redirect("/tasks")

@tasks.route("/edit/<index>", methods = ["GET", "POST"])
@login_required
def edit(index):
    utc = config['general']['utczone']
    dbzone = config['general']['dbzone']
    zone = config['general']['zone']

    if request.method == "GET":
        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
            cursor.execute("""
                SELECT * FROM minicloud_tasks
                WHERE id = %s AND user_id = %s LIMIT 1;
                """, [int(index), int(current_user.id)])

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

            if task['modified']:
                task['modified'] = task['modified'].replace(tzinfo = dbzone).astimezone(zone).strftime('%-d %b %Y')

        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
            cursor.execute("""
                SELECT DISTINCT category AS title FROM minicloud_files
                  WHERE user_id = %s
                UNION SELECT DISTINCT category AS title FROM minicloud_tasks
                  WHERE user_id = %s
                GROUP BY title ORDER BY title ASC;
                """, [ int(current_user.id)
                     , int(current_user.id)
                     ])
            
            categories = cursor.fetchall()

        return render_template( "tasks/edit.html"
                               , config = config
                               , task = task
                               , categories = categories
                               )

    if request.method == "POST":
       
        category = request.form['category']
        status = request.form['status']
        old_status = request.form['task_status']
        old_datetime = request.form['task_datetime']
        description = request.form['description']
        deadline = request.form.get('due')
        annotation = request.form.get('annotation')
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
            
        with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
            try:
                cursor.execute("""
                    UPDATE minicloud_tasks SET
                    status = %s, description = %s, category = %s, annotation = %s, due = %s, done = %s, process = %s
                    WHERE id = %s AND user_id = %s
                    """, [ status
                         , description
                         , category
                         , annotation
                         , due
                         , done
                         , process
                         , int(index)
                         , int(current_user.id)
                         ])

                g.db.commit()
                flash(['Task modified'], 'info')
            
            except:
                g.db.rollback();
        
        return redirect("/tasks")

@tasks.route("/delete/<uid>", methods = ["POST"])
@login_required
def delete(uid):
    with closing(g.db.cursor(cursor_factory = psycopg2.extras.DictCursor)) as cursor:
        try:
            cursor.execute("""
                DELETE FROM minicloud_tasks
                WHERE user_id = %s and uid = %s
                """, [int(current_user.id), uid])

            g.db.commit()
            flash(['Task removed'], 'info')

        except Warning:
            g.db.rollback()

    return redirect("/tasks")
