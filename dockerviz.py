import os
import json

import docker
import pygraphviz as pgv
from flask import Flask

scratchid = '511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158'
if not os.path.isdir('static'):
    os.mkdir('static')
app = Flask(__name__)


@app.route("/")
def hello():
    return """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>dockerviz</title>
  </head>
  <body>
    <h2>dockerviz</h2>
    <ul>
      <li><a href="/containers">/containers</a></li>
      <li><a href="/images">/images</a></li>
    </ul>
  </body>
</html>"""


@app.route("/containers")
def containers():
    c = docker.Client()
    g = pgv.AGraph(rankdir="LR", directed=True, constraint=True)
    g.graph_attr['label'] = r'Running Containers'

    g.add_node('docker', rank=1, shape='star')

    containers = c.containers()

    nametocid = {}
    subgraphs = {}

    for con in containers:
        if len(con['Names']) == 1:
            name = con['Names'][0][1:]
            nametocid[name] = con['Id']
            subgraphs[name] = g.add_subgraph(label=name, rank='same')
            subgraphs[name].add_node(con['Id'],
                                     label='\n'.join((name, con['Image'])),
                                     rank=2, style='bold')

    subgraphs['linked'] = g.add_subgraph(label='linked', rank='same')
    for con in containers:
        if len(con['Names']) > 1:
            print con['Names']
            for name in con['Names']:
                name = name[1:]
                if name.count('/') == 1:
                    parentname = name.split('/')[0]
                if name.count('/') == 0:
                    childname = name
                    nametocid[name] = con['Id']
            subgraphs['linked'].\
                add_node(con['Id'],
                         label='\n'.join((childname, con['Image'])),
                         color='blue', shape='record')
            subgraphs['linked'].add_edge(nametocid[parentname],
                                         nametocid[childname], color='blue')

    for con in containers:
        cid = con['Id']
        cinspect = c.inspect_container(cid)
        privip = cinspect['NetworkSettings']['IPAddress']
        for port in con['Ports']:
            privlabel = ":".join((port['Type'], privip,
                                  str(port['PrivatePort'])))
            privid = cid + privlabel
            g.add_node(privid, label=privlabel, rank=4, shape='box')
            g.add_edge(cid, privid)
            if 'IP' in port:
                publabel = ":".join((port['Type'], port['IP'],
                                    str(port['PublicPort'])))
                g.add_node(publabel, rank=5, shape='cds')
                g.add_edge(privid, publabel)
        g.add_edge('docker', cid, style='dashed', arrowhead='none')

    g.layout('dot')
    g.draw('static/containers.png')
    return app.send_static_file('containers.png')


@app.route("/images")
def images():
    c = docker.Client()
    g = pgv.AGraph(directed=True, splines=True, concentrate=True)
    g.graph_attr['label'] = r'Local Images'

    g.add_node(scratchid, label='scratch', shape='circle')

    images = c.images()

    for image in images:
        if len(image['RepoTags']) == 1 and \
                image['RepoTags'][0] == "<none>:<none>":
            continue
        g.add_node(image['Id'], label='\n'.join(image['RepoTags']))
        hist = c.history(image['Id'])

        # https://github.com/docker/docker-py/pull/319
        if type(hist) != list:
            hist = json.loads(hist)

        lasttag = (image['Id'], 0)
        for idx, img in enumerate(hist[1:]):
            if img['Tags'] is not None:
                g.add_node(img['Id'], label='\n'.join(img['Tags']))
                layers = idx-lasttag[1]
                if layers > 0:
                    g.add_edge(lasttag[0], img['Id'],
                               label=str(layers))
                else:
                    g.add_edge(lasttag[0], img['Id'])
                lasttag = (img['Id'], idx)
            if img['Id'] == scratchid:
                g.add_edge(lasttag[0], scratchid,
                           label=str(idx-lasttag[1]))

    g.layout('fdp')
    g.draw('static/images.png')
    return app.send_static_file('images.png')


if __name__ == "__main__":
    app.run(host='0.0.0.0')
