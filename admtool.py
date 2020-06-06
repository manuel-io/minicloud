#!/usr/bin/env python
import argparse, codecs, psycopg2, psycopg2.extras, bcrypt, os, sys
from config import get_db

commands = {}

def command(name, desc):
    def decorator(func):
        commands.update([(name, { 'name': name, 'desc': desc, 'action': func })])

    return decorator

def requires_db(func):
    def decorator():
        func.__globals__.update({'db': get_db()})
        func()

    return decorator

def requires_args(func):
    def decorator():
        args = commands[sys.argv[1]]
        parser = argparse.ArgumentParser(usage = '%s %s' % (sys.argv[0], args['name']), description = args['desc'])
        func.__globals__.update({'parser': parser})
        func()

    return decorator

@command('command', 'List all commands')
def cmd():
    sys.stderr.write("Commands:\n")
    for item in commands.keys():
        sys.stderr.write("  %s:\t%s\n" % (commands[item]['name'], commands[item]['desc']))

@command('setup', 'Setup Minicloud')
@requires_args
@requires_db
def setup():
    parser.add_argument('--username', default = 'minicloud', metavar = 'USERNAME', help = 'Set username')
    parser.add_argument('--email', default = 'minicloud@example.com', metavar = 'EMAIL', help = 'Set email')
    parser.add_argument('--password', default = 'minicloud', metavar = 'PASSWORD', help = 'Set password')
    args = parser.parse_args(sys.argv[2:]);

    hash = bcrypt.hashpw(args.password, bcrypt.gensalt())
    
    try:
        with db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
                INSERT INTO minicloud_users (name, email, password, admin)
                VALUES (%s, %s, %s, %s)
                """, [args.username, args.email, hash, True])
    
            db.commit()

    except Warning:
        sys.stderr.write('error\n')
        db.rollback()
        
    db.close()

@command('utool', 'Register mulimedia files')
@requires_args
@requires_db
def utool():
    parser.add_argument('csv', metavar = 'CSV FILE', help = 'CSV File')
    args = parser.parse_args(sys.argv[2:]);

    if not os.access(args.csv, os.R_OK):
        sys.stderr.write('Error: file %s is not readable\n' % args.csv)
        exit(1)

    with codecs.open(args.csv, 'r', 'utf-8') as fd:
        for line in fd.readlines():
            mode, typ, category, title, path, mime, director, actors, year = [item.strip() for item in line.split(';')]
    
            if not os.access(path, os.R_OK):
                sys.stderr.write('Error: file %s in csv line is not readable\n' % path)
                exit(1)
            
            try:
                with db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
                    cursor.execute("""INSERT INTO minicloud_multimedia (type, category, title, path, mime, size, director, year)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, [typ, category, title, path, mime, 0, director, year])
                
                db.commit()
                
            except Warning:
                sys.stderr.write('error\n')
                db.rollback()
        
    db.close()

if __name__ == '__main__':

    if len(sys.argv) < 2:
        sys.stderr.write("Usage: %s command [--help]\n" % (sys.argv.pop()))
        exit(1)

    if not sys.argv[1] in commands.keys():
        commands['command']['action']()
        exit(1)

    commands[sys.argv[1]]['action']()
    exit(0)
