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
    'nick': '<button type="button" class="btn btn-sm btn-success">',
    'tonick': '<button type="button" class="btn btn-sm btn-info">',
    'tag': '<button type="button" class="btn btn-sm btn-warning">'
}

@app.route('/get_irc_last', methods=["GET"])
def get_irc_last():

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
    res = sorted(res['hits']['hits'], key=lambda getkey: getkey['sort'][0])

    return json.dumps(res)

@app.route('/')
def home():

    return render_template('gerard.js', style=ircline_style)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
