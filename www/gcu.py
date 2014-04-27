import json
import os
from flask import Flask, render_template, request, url_for, jsonify
from elasticsearch import Elasticsearch

app = Flask(__name__)
es = Elasticsearch()

nlines = 25
es_idx = 'rhonrhon'
channel = 'gcu'

ircline_style = {
    'div': 'ircline',
    'time': 'btn btn-sm btn-default',
    'nick': 'btn btn-sm btn-success',
    'tonick': 'btn btn-sm btn-info',
    'tags': 'btn btn-sm btn-warning'
}

def _res_sort(res):
    '''
    Sort results given by ES using the 'sort' field
    '''
    return sorted(res['hits']['hits'], key=lambda getkey: getkey['sort'][0])

def _get_body(t, d):
    fd = ''
    if d:
        fd = '_fromdate'

    ircbody = {'size': nlines, 'sort': [{'fulldate': {'order': 'desc'}}]}
    ircbody_fromdate = {'query': 
                        {'range': {'fulldate': {'from': d }}},
                        'sort': [{'fulldate': {'order': 'desc'}}]
                       }
    urlbody = {'query':
                {'match': {'urls': 'http https www'}},
                'sort': [{'fulldate': {'order': 'desc'}}],
                'size': nlines
              }
    urlbody_fromdate = {
                        'query': {
                            'bool': {
                                'must': [
                                    {'match': {'urls': 'http www'}},
                                    {'range': {'fulldate': {'from': d }}},
                                ],
                            },
                        },
                        'sort': [{'fulldate': {'order': 'desc'}}],
                        'size': nlines,
                       }

    return locals()['{0}body{1}'.format(t, fd)]

@app.route('/get_last', methods=['GET'])
def get_last():
    '''
    AJAX resource, retrieves latest type lines, or since 'fromdate'

    example:

    curl http://localhost:5000/get_last?t=irc
    curl http://localhost:5000/get_last?t=url&d=2014-04-22T15:07:10.278682
    '''

    if not request.args.get('t'):
        return json.dumps({})

    s_body = _get_body(request.args.get('t'), request.args.get('d'))

    res = es.search(index = es_idx, doc_type = channel, body = s_body)

    return json.dumps(_res_sort(res))

@app.route('/search', methods=['GET'])
def search():
    if not request.args.get('k') or not request.args.get('v'):
        return json.dumps({})

    key = request.args.get('k')
    vals = ' '.join(request.args.get('v').split(','))

    s_body = {'query':
                {'match': {key: {'query': vals, "operator": "and"}}},
                'sort': [{'fulldate': {'order': 'desc'}}],
                'size': nlines
              }
    res = es.search(index = es_idx, doc_type = channel, body = s_body)

    return json.dumps(res['hits']['hits'])

@app.route('/fonts/<path:filename>')
def fonts(filename):
    return app.send_static_file(os.path.join('fonts', filename))

@app.route('/images/<path:filename>')
def images(filename):
    print(os.path.join('images', filename))
    return app.send_static_file(os.path.join('images', filename))

@app.route('/')
def home():

    return render_template('gerard.js', ircline_style=ircline_style)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5080, debug=True)
