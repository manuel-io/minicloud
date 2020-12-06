import psycopg2, psycopg2.extras, io, time, os, re
from flask import Blueprint, g, request, Response
from flask_login import login_required, current_user
from datetime import datetime
from dateutil import tz, parser
from config import Config

def format_registered(user):
    utc = Config.UTCZONE
    zone = Config.ZONE
    user['registered'] = user['created_at'].replace(tzinfo=utc).astimezone(zone).strftime("%Y-%m-%d")
    return user

def format_task(task):
    utc = Config.UTCZONE
    zone = Config.ZONE
    today = datetime.utcnow().replace(tzinfo=utc).astimezone(zone)
    task['delayed'] = False

    if task['process']:
        task['process'] = parser.parse(task['process']).replace(tzinfo=utc).astimezone(zone).strftime("%-d %b %Y")

    if task['done']:
        task['done'] = parser.parse(task['done']).replace(tzinfo=utc).astimezone(zone).strftime("%-d %b %Y")

    if task['due']:
      delta = parser.parse(task['due']).replace(tzinfo=utc).astimezone(zone) - today
      task['deadline'] = round(delta.total_seconds()/86400)
      task['delayed'] = True if task['deadline'] < 0 else False
      task['due'] = parser.parse(task['due']).replace(tzinfo=utc).astimezone(zone).strftime("%-d %b %Y")

    return task

def get_task_types():
    return [ { 'name': 'Pending', 'value': 'pending' }
           , { 'name': 'Processing', 'value': 'processing' }
           , { 'name': 'Completed', 'value': 'completed' }
           , { 'name': 'Deleted', 'value': 'deleted' }
           ]

def get_media_types():
    return [ { 'name': 'Audiobooks', 'value': 'audiobooks' }
           , { 'name': 'Audiotracks', 'value': 'audiotracks' }
           , { 'name': 'Ballets', 'value': 'ballets' }
           , { 'name': 'Documentaries', 'value': 'documentaries' }
           , { 'name': 'Movies', 'value': 'movies' }
           , { 'name': 'Musicals', 'value': 'musicals' }
           , { 'name': 'Series', 'value': 'series' }
           , { 'name': 'Videoclips', 'value': 'videoclips' }
           ]

@login_required
def get_categories():
    categories = []
    try:
        with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
            SELECT DISTINCT category FROM minicloud_gallery
              WHERE user_id = %s
            UNION SELECT DISTINCT category FROM minicloud_tasks
              WHERE user_id = %s
            UNION SELECT DISTINCT category FROM minicloud_notes
              WHERE user_id = %s
            GROUP BY category ORDER BY category ASC;
            """, [int(current_user.id), int(current_user.id),  int(current_user.id)])

            categories = cursor.fetchall()

    except Exception as e:
        raise e

    return categories

def get_stream(request, filename, oid, mime, size):
    try:
        if request.headers.has_key("Range"):
            begin, end = 0, size - 1
            ranges = re.findall(r"\d+", request.headers["Range"])

            if ranges[0]:
                begin = int(ranges[0])
                length = end - begin + 1

            if len(ranges) > 1:
                end = int(ranges[1])
                length = end - begin + 1

            if begin > end:
                raise ValueError

            lobj = g.db.lobject(oid, 'rb')
            lobj.seek(begin)
            stream = io.BytesIO(lobj.read(length))
            stream_size = stream.getbuffer().nbytes
            lobj.close()

            response = Response(stream, 206, mimetype=data_mime, direct_passthrough=True)
            response.headers.add('Accept-Ranges', 'bytes')
            response.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(begin, begin + length - 1, size))
            response.headers.add('Content-Length', str(length))
            response.headers.add('Content-Disposition', 'attachment', filename=filename)

            return response

        else:
            lobj = g.db.lobject(oid, 'rb')
            lobj.seek(0)
            stream = io.BytesIO(lobj.read())
            stream_size = stream.getbuffer().nbytes
            length = size
            lobj.close()

            response = Response(stream, 200, mimetype=mime, direct_passthrough=True)
            response.headers.add('Accept-Ranges', 'bytes')
            response.headers.add('Content-Length', str(length))
            response.headers.add('Content-Disposition', 'attachment', filename=filename)

            return response

    except Exception as e:
        raise e
