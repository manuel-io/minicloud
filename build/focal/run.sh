#!/bin/bash
docker build -t minicloud_focal .
docker run --network host -d -P --name cloud_on_focal minicloud_focal
