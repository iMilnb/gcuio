import os
import re
from flask import Flask, render_template, request, url_for, json, Response
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

# match ISO format - datetime.datetime.utcnow().isoformat()
# i.e. 2014-04-30T18:22:42.596996
isodaterx = '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+$'

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
                                    {'match': {'urls': 'http https www'}},
                                    {'range': {'fulldate': {'from': d }}},
                                ],
                            },
                        },
                        'sort': [{'fulldate': {'order': 'desc'}}],
                        'size': nlines,
                       }

    try:
        ret = locals()['{0}body{1}'.format(t, fd)]
    except:
        ret = None
    return ret

@app.route('/get_last', methods=['GET'])
def get_last():
    '''
    AJAX resource, retrieves latest type lines, or since 'fromdate'

    example:

    curl http://localhost:5000/get_last?t=irc
    curl http://localhost:5000/get_last?t=url&d=2014-04-22T15:07:10.278682
    '''

    allow_t = ['irc', 'url']
    d = request.args.get('d')
    t = request.args.get('t')

    if t in allow_t:
        if d and not re.search(isodaterx, d):
            d = ''

        s_body = _get_body(t, d)
    
        res = es.search(index = es_idx, doc_type = channel, body = s_body)
    
        return Response(json.dumps(_res_sort(res)), mimetype='application/json')

    # unknown type
    return json.dumps({})

@app.route('/search', methods=['GET'])
def search():
    # no query
    if not request.args.get('q'):
        return json.dumps({})

    if request.args.get('f'):
        f = request.args.get('f')
    else:
        f = 0

    fields = ['nick', 'tonick', 'line', 'tags', 'urls', 'date']
    q = request.args.get('q')

    s_body = {'query': {
                        'query_string': {'query': q},
                },
                'from': f,
                'size': nlines
             }

    res = es.search(index = es_idx, doc_type = channel, body = s_body)

    return Response(json.dumps(res['hits']), mimetype='application/json')

@app.route('/fonts/<path:filename>')
def fonts(filename):
    return app.send_static_file(os.path.join('fonts', filename))

@app.route('/images/<path:filename>')
def images(filename):
    print(os.path.join('images', filename))
    return app.send_static_file(os.path.join('images', filename))

@app.route('/')
def home():

    return render_template('gerard.js',
                            ircline_style=ircline_style, nlines=nlines)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5080, debug=True)
    #app.run(host='0.0.0.0', port=5080)
