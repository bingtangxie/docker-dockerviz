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
    <h1>dockerviz</h1>
    <ul>
      <li><h2><a href="/containers">/containers</a></h2></li>
      <li><h2><a href="/images">/images</a></h2></li>
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
    volumes = {}

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
            parents = []
            for name in con['Names']:
                name = name[1:]
                if name.count('/') == 1:
                    parents.append(name.split('/')[0])
                if name.count('/') == 0:
                    childname = name
                    nametocid[name] = con['Id']
            subgraphs['linked'].\
                add_node(con['Id'],
                         label='\n'.join((childname, con['Image'])),
                         color='blue')
            for parent in parents:
                subgraphs['linked'].add_edge(nametocid[parent],
                                             nametocid[childname],
                                             color='blue')

    for con in containers:
        cid = con['Id']
        cinspect = c.inspect_container(cid)
        privip = cinspect['NetworkSettings']['IPAddress']
        for port in con['Ports']:
            privlabel = ":".join((port['Type'], privip,
                                  str(port['PrivatePort'])))
            privid = cid + privlabel
            g.add_node(privid, label=privlabel, rank=4, shape='box',
                       color='orange')
            g.add_edge(cid, privid)
            if 'IP' in port:
                publabel = ":".join((port['Type'], port['IP'],
                                    str(port['PublicPort'])))
                g.add_node(publabel, rank=5, shape='cds', color='red')
                g.add_edge(privid, publabel)
        g.add_edge('docker', cid, style='dashed', arrowhead='none')
        for vol, vid in cinspect['Volumes'].iteritems():
            if vid not in volumes:
                volumes[vid] = vol
                g.add_node(vid, label=vol, shape='box3d', rank=3,
                           color='darkgreen')
            g.add_edge(cid, vid)

    g.layout('dot')
    g.draw('static/containers.png')
    return app.send_static_file('containers.png')


@app.route("/images")
def images():
    c = docker.Client()
    g = pgv.AGraph(directed=True, splines=True, concentrate=True)
    g.graph_attr['label'] = r'Local Images'

    images = c.images()

    for image in images:
        if image['RepoTags'] is None:
            continue
        hist = c.history(image['Id'])

        # https://github.com/docker/docker-py/pull/319
        if type(hist) != list:
            hist = json.loads(hist)

        for idx, img in enumerate(hist):
            if img['Tags'] is not None:
                g.add_node(img['Id'], label='\n'.join(img['Tags']))
            else:
                if img['Id'] == scratchid:
                    g.add_node(img['Id'], label=img['Id'][0:12],
                               shape='circle')
                else:
                    g.add_node(img['Id'], label=img['Id'][0:12])

            if idx != 0:
                g.add_edge(hist[idx-1]['Id'], img['Id'])

    # clean up irrelevant layers
    changed = 1
    while (changed > 0):
        changed = 0
        for node in g.nodes():
            successors = g.successors(node)
            predecessors = g.predecessors(node)
            if len(successors) == 1 and len(predecessors) == 1:
                g.delete_node(node)
                g.add_edge(predecessors[0], successors[0])
                changed += 1

    g.layout('fdp')
    g.draw('static/images.png')
    return app.send_static_file('images.png')


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
