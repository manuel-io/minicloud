#!/bin/bash
service postgresql start \
  && service nginx start \
  && service ssh start \
  && service rsyslog restart \
  && service minidlna restart \
  && service minicloud start
