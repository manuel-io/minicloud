#!/bin/bash

mkdir -p /var/minicloud/postgresql
chown -R postgres:postgres /var/minicloud/postgresql/

rm -rf /var/minicloud/postgresql/{*,.*}
su postgres -c '/usr/bin/pg_ctl -D /var/minicloud/postgresql stop'

su postgres -c '/usr/bin/initdb --locale=C.UTF-8 --encoding=UTF-8 -D /var/minicloud/postgresql'
su postgres -c '/usr/bin/postgres -D /var/minicloud/postgresql -p 5432 &'
sleep 10
