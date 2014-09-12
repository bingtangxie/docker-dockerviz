from python:2

maintainer Peter Salvatore 

run apt-get update -yqq && apt-get install -yqq graphviz

copy requirements.txt /usr/src/app/
copy dockerviz.py /usr/src/app/

workdir /usr/src/app

run pip install -r requirements.txt

cmd python2 dockerviz.py
