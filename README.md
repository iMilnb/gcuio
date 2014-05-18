### GCUio

_The new GCU-Squad! freak_

_GCUio_ is meant to expose _GCU-Squad!_ IRC channel publicly, on the web.  
It consists of:
  * An IRC bot, whose duty is to dump IRC data to an [Elasticsearch](http://www.elasticsearch.org) database
  * A simple web server written with [Flask](http://flask.pocoo.org/) who responds to _JavaScript_ queries by fetching data in the _ElasticSearch_ database
  * A GUI written with [BootStrap](http://getbootstrap.com/) and [JQuery](http://jquery.com/)

### Interact with _GCUio_

Apart from the web interface, which is self explanatory, _GCUio_ can be queried
using [REST](http://en.wikipedia.org/wiki/Representational_state_transfer)-like
_URIs_, and will reply using [JSON](http://en.wikipedia.org/wiki/JSON):

Obtain latest _IRC_ entries:

    $ curl 'gcu.io/g/irc'

Obtain latest posted _URL_:

    $ curl 'gcu.io/g/url'

Search for latest comments made by nickname `foo`:

    $ curl 'gcu.io/s/n/foo'

Search for latest comments by `bar` with the `nsfw` tag:

    $ curl 'gcu.io/s/n/bar/t/nsfw'

Search for lines containing `curl` from and to certain dates:

    $ curl 'gcu.io/s/l/curl/from/2010-02-23/to/2011-01-01'

The following filters are available:

    rqueries = {
        'n': 'nick:',
        't': 'tags:',
        'l': 'line:',
        'u': 'urls:',
        'from': 'date:>',
        'to': 'date:<'
    }

