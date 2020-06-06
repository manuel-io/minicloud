FROM ubuntu:bionic
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
                                                      
RUN mkdir /var/run/sshd
RUN locale-gen de_DE.UTF-8 en_US.UTF-8 en_GB.UTF-8
RUN groupadd -g 9001 minicloud
RUN useradd -u 9001 -g 9001 -d /home/minicloud -m -s /bin/bash minicloud
RUN service postgresql start && sleep 10 && su postgres -c 'createuser -w -d minicloud' && su postgres -c 'createdb -O minicloud minicloud'

COPY share/pg_hba.conf /etc/postgresql/10/main/pg_hba.conf
COPY share/minidlna.conf /etc/minidlna.conf
COPY . /home/minicloud

RUN chown -R minicloud:www-data /home/minicloud
RUN service postgresql start && sleep 10 && su minicloud -c 'psql < /home/minicloud/share/schema.sql'
RUN su - minicloud -c 'python3 -m venv /home/minicloud'
RUN su - minicloud -c '/home/minicloud/bin/pip install -r /home/minicloud/requirements.txt'
RUN service postgresql start && sleep 10 && su - minicloud -c '/home/minicloud/bin/python /home/minicloud/admtool.py'

RUN cp /home/minicloud/share/docker.service /etc/init.d/minicloud
RUN chmod a+x /etc/init.d/minicloud
RUN cp /home/minicloud/share/docker.nginx /etc/nginx/sites-available/minicloud
RUN rm /etc/nginx/sites-enabled/default
RUN ln -s /etc/nginx/sites-available/minicloud /etc/nginx/sites-enabled/minicloud

ADD share/docker.sh /startup.sh

EXPOSE 80

CMD ["/bin/bash", "/startup.sh"]
