import psycopg2, psycopg2.extras, io, time, os, re
from PIL import Image, ImageOps
from flask import Blueprint, url_for, redirect, g, render_template, send_file, request, flash, send_from_directory, Response, abort
from flask_login import UserMixin, login_required, current_user
from config import config, MIME_SUFFIX

@login_required
def get_categories():
    with g.db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
        cursor.execute("""
            SELECT DISTINCT category FROM minicloud_gallery
                WHERE user_id = %s
            UNION SELECT DISTINCT category FROM minicloud_tasks
                WHERE user_id = %s
            GROUP BY category ORDER BY category ASC;
            """, [ int(current_user.id)
                 , int(current_user.id) ])

        return cursor.fetchall()

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
