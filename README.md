# Requirements

    sudo apt install git \
                     libpq-dev \
                     python3-dev \
                     python3-venv \
                     python3-pip

# Quick Start

    sudo groupadd -g 9001 minicloud
    useradd -u 9001 -g 9001 -d /home/minicloud -m -s /bin/bash minicloud
    sudo -u postgres createuser -P -d minicloud
    sudo -u postgres createdb -O minicloud minicloud

    su - minicloud
    cd ~

    git clone mincloud /home/minicloud
    python3 -m venv /home/minicloud

    psql < /home/minicloud/share/schema.sq

    cp /home/minicloud/share/minicloud.service /etc/systemd/system/minicloud.service
    cp /home/minicloud/share/minicloud.nginx /etc/nginx/sites-available/minicloud

    systemctl restart nginx.service
    systemctl restart minicloud.service

# Dockerfile
    
    git clone https://github.com/manuel-io/minicloud.git minicloud_docker
    docker build -t minicloud .
    docker run -d -p 8080:80 --name minicloud minicloud:latest

# SimpleLightbox

SimpleLightbox (https://github.com/andreknieriem/simplelightbox) is licensed
under the MIT License (MIT)

# Font Awesome

Graphic files under static/fontawsame are a product of the Font Awesome
library (https://fontawesome.com/) and distributed under the Creative Commons
Attribution BY 4.0 International license (https://fontawesome.com/license/free)

# Lato Font

The main font in the default
design is from the Lato font
family and licensed under SIL Open Font License 1.1
(https://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&id=OFL)
