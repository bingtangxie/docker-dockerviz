dockerviz
===========

![Image](../blob/master/containers.png?raw=true)

A quick experiment in generating graphs of containers and images using
docker-py and pygraphviz.  It is wrapped up as a Flask app and shipped as a
Docker image which you can run directly, for example:

    $ docker run -d --name dockerviz -p 5000:5000 \
                 -v /var/run/docker.sock:/var/run/docker.sock \
                 psftw/dockerviz

*NOTE: if you have a lot of images or running containers, this will generate
very large PNG files that could crash your browser.*
