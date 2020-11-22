#!/bin/sh

# Generate host keys if not present
ssh-keygen -A
su postgres -c '/usr/lib/postgresql/12/bin/postgres -D /var/minicloud/postgresql -p 5432 &'

/etc/init.d/minicloud start
/usr/sbin/minidlnad
/usr/sbin/nginx
/usr/sbin/sshd -D -e "$@"
