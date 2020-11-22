#!/bin/bash
docker run --network host -d -P --name cloud_on_centos8 minicloud_centos8

sleep 10

curl -I localhost/login 2> /dev/null | grep '501'
curl -I localhost:8290 2> /dev/null | grep '401'

sleep 10

docker stop cloud_on_centos8
docker rm cloud_on_centos8
