FROM ubuntu:focal
RUN apt-get update && apt upgrade -y

# BUILD TOOLS
RUN apt-get install -y libpq-dev \
                       python3-dev \
                       python3-venv \
                       python3-pip

# SERVER TOOLS
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql \
                                                      nginx-full \
                                                      minidlna

RUN apt-get install -y ssh rsyslog
RUN echo 'root:minicloud' | chpasswd

RUN mkdir /var/run/sshd
RUN mkdir -p /var/minicloud/multimedia
RUN mkdir -p /var/minicloud/multimedia/movies
RUN mkdir -p /var/minicloud/multimedia/series
RUN mkdir -p /var/minicloud/multimedia/clips
RUN mkdir -p /var/minicloud/multimedia/videoclips
RUN mkdir -p /var/minicloud/multimedia/tracks
RUN mkdir -p /var/minicloud/multimedia/audiotracks
RUN mkdir -p /var/minicloud/multimedia/documentary

RUN locale-gen de_DE.UTF-8 en_US.UTF-8 en_GB.UTF-8
RUN groupadd -g 9001 minicloud
RUN useradd -u 9001 -g 9001 -d /home/minicloud -m -s /bin/bash minicloud
RUN echo 'minicloud:minicloud' | chpasswd
RUN service postgresql start && sleep 10 && su postgres -c 'createuser -w -d minicloud' && su postgres -c 'createdb -O minicloud minicloud'

COPY share/pg_hba.conf /pg_hba.conf
COPY share/copy_hba.sh /copy_hba.sh
COPY share/minidlna.conf /etc/minidlna.conf
COPY share/minidlna.default /etc/default/minidlna
COPY . /home/minicloud

RUN chown -R minicloud:minicloud /home/minicloud
RUN chown -R minicloud:minicloud /var/minicloud
RUN service postgresql start && sleep 10 && su minicloud -c 'psql < /home/minicloud/share/schema.sql'
RUN su - minicloud -c 'python3 -m venv /home/minicloud'
RUN su - minicloud -c '/home/minicloud/bin/pip install wheel'
RUN su - minicloud -c '/home/minicloud/bin/pip install -r /home/minicloud/requirements.txt'
RUN service postgresql start && sleep 10 && /bin/bash /copy_hba.sh
RUN service postgresql start && sleep 10 && su - minicloud -c '/home/minicloud/bin/python /home/minicloud/admtool.py setup --username minicloud --password minicloud'

RUN cp /home/minicloud/share/docker.service /etc/init.d/minicloud
RUN chmod a+x /etc/init.d/minicloud
RUN cp /home/minicloud/share/docker.nginx /etc/nginx/sites-available/minicloud
RUN rm /etc/nginx/sites-enabled/default
RUN ln -s /etc/nginx/sites-available/minicloud /etc/nginx/sites-enabled/minicloud

COPY share/docker.sh /startup.sh

EXPOSE 22
EXPOSE 80
EXPOSE 8200

CMD ["/bin/bash", "/startup.sh"]
