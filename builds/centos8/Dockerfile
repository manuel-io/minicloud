FROM centos:centos8

RUN dnf install -y gcc postgresql-libs postgresql-devel
RUN dnf install -y python3-devel python3-virtualenv python3-pip
RUN dnf install -y openssh-server rsyslog nginx
RUN dnf install -y postgresql-server postgresql-contrib
RUN dnf install -y git vim tmux

RUN echo "root:root" | chpasswd
RUN mkdir /var/run/sshd

COPY entrypoint.sh /
COPY install.sh /
COPY install_postgresql.sh /
COPY install_nginx.sh /
COPY install_minidlna.sh /
COPY minicloud.init /etc/init.d/minicloud

RUN chmod u+x /entrypoint.sh
RUN chmod u+x /etc/init.d/minicloud

RUN echo /install.sh
RUN /bin/bash /install.sh

EXPOSE 22
EXPOSE 80
EXPOSE 8290
ENTRYPOINT ["/entrypoint.sh"]
