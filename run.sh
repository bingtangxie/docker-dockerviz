#!/bin/bash

docker kill dockerviz
docker rm dockerviz
docker run -d --name dockerviz -p 5000:5000 \
           -v /var/run/docker.sock:/var/run/docker.sock \
           -v $(pwd):/usr/src/app \
              psftw/dockerviz
