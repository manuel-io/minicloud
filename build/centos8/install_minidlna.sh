#!/bin/bash

mkdir -p /var/minicloud/multimedia
mkdir -p /var/minicloud/multimedia/audiobooks
mkdir -p /var/minicloud/multimedia/audiotracks
mkdir -p /var/minicloud/multimedia/ballets
mkdir -p /var/minicloud/multimedia/documentaries
mkdir -p /var/minicloud/multimedia/movies
mkdir -p /var/minicloud/multimedia/musicals
mkdir -p /var/minicloud/multimedia/series
mkdir -p /var/minicloud/multimedia/videoclips

chown -R minicloud:minicloud /var/minicloud/multimedia
chmod -R a+rx /var/minicloud/multimedia

cat > /etc/default/minidlna << BLOCK
  START_DAEMON="yes"
  CONFIGFILE="/etc/minidlna.conf"
  LOGFILE="/var/log/minidlna.log"
  USER="minicloud"
  GROUP="minicloud"
  DAEMON_OPTS="-r"
BLOCK

cat > /etc/minidlna.conf << BLOCK
  network_interface=lo
  user=minicloud
  media_dir=AV,/var/minicloud/multimedia/audiobooks
  media_dir=AV,/var/minicloud/multimedia/audiotracks
  media_dir=AV,/var/minicloud/multimedia/ballets
  media_dir=AV,/var/minicloud/multimedia/documentaries
  media_dir=AV,/var/minicloud/multimedia/movies
  media_dir=AV,/var/minicloud/multimedia/musicals
  media_dir=AV,/var/minicloud/multimedia/series
  media_dir=AV,/var/minicloud/multimedia/videoclips
  db_dir=/var/minicloud/minidlna
  log_dir=/var/log
  root_container=B
  port=8200
  friendly_name=Minicloud
  inotify=yes
  max_connections=5
BLOCK
