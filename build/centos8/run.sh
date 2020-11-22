#!/bin/bash
docker build -t minicloud_centos8 .
docker run --network host -d -P --name cloud_on_centos8 minicloud_centos8
