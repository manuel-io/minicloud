#!/bin/bash
if [[ $(id -u) -ne 0 ]] ; then echo "Please run with root privileges"; exit 1; fi

minicloud_id=9001
minicloud_usr="minicloud"
minicloud_pwd="minicloud"
minicloud_base="/home/${minicloud_usr}"

groupadd -g $minicloud_id $minicloud_usr
useradd -u $minicloud_id -g $minicloud_id -d $minicloud_base -m -s /bin/bash $minicloud_usr
echo "${minicloud_usr}:${minicloud_pwd}" | chpasswd

mkdir -p /var/minicloud/service
chown -R minicloud:minicloud /var/minicloud
chmod a+rx /var/minicloud
chmod a+rx /var/minicloud/service

. /install_postgresql.sh
. /install_nginx.sh
. /install_minidlna.sh

rm -rf $minicloud_base/{*,.*}
git clone https://github.com/manuel-io/minicloud.git $minicloud_base
chown -R $minicloud_usr:$minicloud_usr $minicloud_base

su $minicloud_usr -c "python3 -m venv ${minicloud_base}"
su $minicloud_usr -c "${minicloud_base}/bin/pip install --upgrade pip"
su $minicloud_usr -c "${minicloud_base}/bin/pip install wheel"
su $minicloud_usr -c "${minicloud_base}/bin/pip install -r ${minicloud_base}/requirements.txt"

su postgres -c "createuser -w -d ${minicloud_usr}"
su postgres -c "createdb -T template0 --locale=C.UTF-8 --encoding=UTF-8 -O ${minicloud_usr} ${minicloud_usr}"

su $minicloud_usr -c "psql < ${minicloud_base}/share/schema.sql"
su $minicloud_usr -c "${minicloud_base}/bin/python ${minicloud_base}/admtool.py setup --username ${minicloud_usr} --password ${minicloud_usr}"
