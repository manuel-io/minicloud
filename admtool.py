#!/usr/bin/env python
import functools, argparse, codecs, psycopg2, psycopg2.extras, bcrypt, os, sys
from config import Config
from multimedia import find_minidlna_files

commands = []

if len(sys.argv) < 2:
    sys.stderr.write("Usage: %s command [--help]\n" % (sys.argv.pop()))
    exit(1)

def command(name, desc):
    def inner(func):
        commands.append({ 'name': name, 'desc': desc, 'action': func })

    return inner

@command('command', 'List all commands')
def cmd(cmd):
    sys.stderr.write("Commands:\n")
    for cmd in commands:
        sys.stderr.write("  %s:\t%s\n" % (cmd['name'], cmd['desc']))

@command('minicloud', 'System status variables')
def minidloud(cmd):
    parser = argparse.ArgumentParser(usage = '%s %s' % (sys.argv[0], cmd['name']), description = cmd['desc'])
    parser.add_argument('--version', '-v',  help = 'Show system version', action = 'store_true')
    args = parser.parse_args(sys.argv[2:]);

    if args.version:
        sys.stderr.write('%s.%s.%s\n' % (Config.RELEASE['major'], Config.RELEASE['minor'], Config.RELEASE['revision']))

@command('users', 'List system users')
def auths(cmd):
    parser = argparse.ArgumentParser(usage = '%s %s' % (sys.argv[0], cmd['name']), description = cmd['desc'])
    parser.add_argument('--username', default = '%', metavar = 'USERNAME', help = 'Set username')
    args = parser.parse_args(sys.argv[2:]);
    db = Config.get_db()
    data = []

    try:
        with db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
              SELECT * FROM minicloud_users AS a
              WHERE a.name LIKE %s
              """, [args.username])

            data = cursor.fetchall();

        for user in data:
            sys.stdout.write('Username: %s\n' % user['name'])
            sys.stdout.write('E-Mail: %s\n' % user['email'])
            sys.stdout.write('Disabled: %s\n' % user['disabled'])
            sys.stdout.write('Activation key: %s\n' % user['activation_key'])
            sys.stdout.write('Admin: %s\n' % user['admin'])
            sys.stdout.write('Media: %s\n' % user['media'])

    except Exception as e:
        sys.stderr.write('Error: %s\n' % e)

    db.close()

@command('setup', 'Setup Minicloud')
def setup(cmd):
    parser = argparse.ArgumentParser(usage = '%s %s' % (sys.argv[0], cmd['name']), description = cmd['desc'])
    parser.add_argument('--username', default = 'minicloud', metavar = 'USERNAME', help = 'Set username')
    parser.add_argument('--email', default = 'minicloud@example.com', metavar = 'EMAIL', help = 'Set email')
    parser.add_argument('--password', default = 'minicloud', metavar = 'PASSWORD', help = 'Set password')
    args = parser.parse_args(sys.argv[2:]);
    db = Config.get_db()

    hash = bcrypt.hashpw(args.password, bcrypt.gensalt())

    try:
        with db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
                INSERT INTO minicloud_users (name, email, password, admin)
                VALUES (%s, %s, %s, %s)
                """, [args.username, args.email, hash, True])

        db.commit()

    except Exception as e:
        db.rollback()
        sys.stderr.write('Error: %s\n' % e)

    db.close()

@command('utool', 'Update mulimedia entries')
def utool(cmd):
    parser = argparse.ArgumentParser(usage = '%s %s' % (sys.argv[0], cmd['name']), description = cmd['desc'])
    parser.add_argument('csv', metavar = 'CSV FILE', help = 'CSV File')
    args = parser.parse_args(sys.argv[2:]);
    db = Config.get_db()

    if not os.access(args.csv, os.R_OK):
        sys.stderr.write('Error: file %s is not readable\n' % args.csv)
        exit(1)

    with codecs.open(args.csv, 'r', 'utf-8') as fd:
        lines = fd.readlines()
        first = lines.pop(0).strip().split(';')
        keys = ','.join(list(map(lambda key: '%s' % key.strip(), first)))

        for line in lines:
            first = line.strip().split(';')
            values = ','.join(list(map(lambda value: '\'%s\'' % value.strip(), first)))
            query = "INSERT INTO minicloud_multimedia (%s) VALUES (%s)" % (keys, values)

            try:
                with db.cursor(cursor_factory = psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query)

                db.commit()

            except Exception as e:
                db.rollback()
                sys.stderr.write('Error: %s\n' % e)

    db.close()

if __name__ == '__main__':
    keys = list(map(lambda cmd: cmd['name'], commands))
    if not sys.argv[1] in keys:
        cmd = functools.reduce(lambda acc, val: val if val['name'] == 'command' else acc, commands, None)
        cmd['action'](cmd)
        exit(1)

    cmd = functools.reduce(lambda acc, val: val if val['name'] == sys.argv[1] else acc, commands, None)
    if cmd and cmd['name'] == sys.argv[1]:
        cmd['action'](cmd)
