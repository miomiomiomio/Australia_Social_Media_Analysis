from flask import Flask, request
import couchdb
from couchdb import design
import json
import flask

# start the web service.
app = Flask(__name__,static_url_path='')

# home page
@app.route('/', methods=['GET'])
def root():
    return app.send_static_file('home.html')

# map view data correlation page
@app.route('/mapview', methods=['GET'])
def do_system():
    return app.send_static_file('mapview.html')

# map view of lust
@app.route('/lustmap', methods=['GET'])
def do_system1():
    return app.send_static_file('lustmap.html')

def query_all(db):
    qlist = []
    for doc in db:
        qlist.append(doc)
    return qlist

# get all data with specified database name
@app.route('/database/<string:db_name>', methods=["GET"])
def query_all(db_name):
    couch = couchdb.Server('http://127.0.0.1:5984')
    querydb = couch(db_name)
    data_res = {"data": query_all(querydb)}
    res = flask.make_response(flask.jsonify(data_res))
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Methods'] = 'GET'
    res.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type'
    return res

if __name__ == '__main__':
    app.run(debug=True)
