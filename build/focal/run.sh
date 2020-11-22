#!/bin/bash
docker run --network host -d -P --name cloud_on_focal minicloud_focal

sleep 10

curl -I localhost/login 2> /dev/null | grep '501'
curl -I localhost:8290 2> /dev/null | grep '401'

sleep 10

docker stop cloud_on_focal
docker rm cloud_on_focal
