import json
from flask import Flask, render_template, request, url_for
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

@app.route('/get_url_last')
def get_url_last():
    '''
    AJAX resource, retrieves latest records containing URLs

    example: curl http://localhost:5000/get_url_last
    '''
    res = es.search(
                index = es_idx,
                doc_type = channel,
                body = {'query':
                            {'match': {'urls': 'http www'}},
                            'sort': [{'fulldate': {'order': 'desc'}}],
                        'size': nlines
                       }
            )
    return json.dumps(_res_sort(res))

@app.route('/get_irc_last', methods=["GET"])
def get_irc_last():
    '''
    AJAX resource, retrieves latest IRC lines, or IRC since 'fromdate'

    example:

    curl http://localhost:5000/get_irc_last
    curl http://localhost:5000/get_url_last?fromdate=2014-04-22T15:07:10.278682
    '''
    fromdate = None
    if request.args.get('fromdate'):
        fromdate = request.args.get('fromdate')
        s_body = {'query': 
                    {'range':
                        {'fulldate':
                            {'from': fromdate }
                        }
                    },
                  'sort': [{'fulldate': {'order': 'desc'}}]
                 }
    else:
        s_body = {'size': nlines, 'sort': [{'fulldate': {'order': 'desc'}}]}

    res = es.search(index = es_idx, doc_type = channel, body = s_body)

    return json.dumps(_res_sort(res))

@app.route('/')
def home():

    return render_template('gerard.js', ircline_style=ircline_style)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
