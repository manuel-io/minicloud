FROM ubuntu:focal

RUN DEBIAN_FRONTEND=noninteractive apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y libpq-dev python3-dev python3-venv python3-pip
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql nginx-full minidlna ssh rsyslog
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y git vim tmux

RUN echo 'root:root' | chpasswd
RUN mkdir /var/run/sshd

COPY entrypoint.sh /
COPY install.sh /
COPY install_postgresql.sh /
COPY install_nginx.sh /
COPY install_minidlna.sh /
COPY minicloud.init /etc/init.d/minicloud

RUN chmod u+rx /entrypoint.sh
RUN chmod u+rx /etc/init.d/minicloud
RUN /bin/bash /install.sh

EXPOSE 22
EXPOSE 80
EXPOSE 8290

CMD ["/bin/bash", "/entrypoint.sh"]
