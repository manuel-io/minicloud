## General

Starting with a new `minicloud` project requires some initial system
adjustments. Which in any case also needs root privileges.

1) New user and group

  At first create a new system group `minicloud` and a new user `minicloud`:

    groupadd -g 9001 minicloud
    useradd -u 9001 -g 9001 -d /home/minicloud -m -s /bin/bash minicloud

  In this example the app shall be deployed in the home directory
  `/home/minicloud`. Of course the desired shell can be customized if
  necessary. You can optionally set a password with `passwd minicloud`.

2) Installing a Database connection

  Installing a new Database or using ENVIRONMENT variables to specify a db
  connection is necessary. Almost all user content of the minicloud is stored in
  a database. Create a new user and a related database:

    su postgres -c 'createuser -w -d minicloud'
    su postgres -c 'createdb -T template0 -l 'en_US.UTF-8' -E 'UTF-8' -O minicloud minicloud'

  Optionally a password can be set if '-w' is replaced by '-W'. If user and
  database run on the same system, a password with the correct configuration is
  not required. Example file: `pg_hba.conf`.

3) Installing a Database schema

  The new database must be initialized with the correct database schema:

      su minicloud -c 'psql < /home/minicloud/share/schema.sql'
