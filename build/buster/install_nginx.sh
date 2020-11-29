#!/bin/bash

grep 'www-data' /etc/passwd || useradd -r www-data
chown -R www-data:www-data /var/lib/nginx

cat > /etc/nginx/nginx.conf <<BLOCK
user www-data;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /var/run/nginx.pid;

# Load dynamic modules. See /usr/share/doc/nginx/README.dynamic.
include /usr/share/nginx/modules/*.conf;

events {
  worker_connections 1024;
}

http {
  log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                  '\$status \$body_bytes_sent "\$http_referer" '
                  '"\$http_user_agent" "\$http_x_forwarded_for"';

  access_log /var/log/nginx/access.log main;
  sendfile            on;
  tcp_nopush          on;
  tcp_nodelay         on;
  keepalive_timeout   65;
  types_hash_max_size 2048;

  include             /etc/nginx/mime.types;
  default_type        application/octet-stream;

  # Load modular configuration files from the /etc/nginx/conf.d directory.
  # See http://nginx.org/en/docs/ngx_core_module.html#include
  include /etc/nginx/conf.d/*.conf;

  server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;
    client_max_body_size 0;
    client_body_timeout 300s;

    location / {
      include uwsgi_params;
      uwsgi_read_timeout 600s;
      uwsgi_send_timeout 300s;
      uwsgi_pass unix:/var/minicloud/service/minicloud.sock;
    }
  }

  # Proxy local Minidlna
  server {
    listen 8290 default_server;
    listen [::]:8290 default_server;
    server_name _;

    location / {
      if (\$args ~ 'auth=([\d\w]+)') {
        set \$auth \$1;
      }

      if (\$http_x_auth_token) {
        set \$auth \$http_x_auth_token;
      }

      auth_request /auth;
      auth_request_set \$auth_status \$upstream_status;
      postpone_output 0;
      proxy_cache off;
      proxy_pass http://127.0.0.1:8200;
      add_header 'Access-Control-Allow-Origin' '*';
    }

    location = /auth {
      internal;

      proxy_pass http://127.0.0.1/auths/verify;
      proxy_pass_request_body off;
      proxy_set_header Content-Length '';
      proxy_set_header X-Original-URI \$request_uri;
      proxy_set_header X-Auth-Token \$auth;
    }
  }
}
BLOCK
