GCUio
=====

_The new GCU-Squad! freak_

_GCUio_ is meant to expose _GCU-Squad!_ IRC channel publicly, on the web.  
It consists of:
  * An IRC bot, whose duty is to dump IRC data to an [Elasticsearch](http://www.elasticsearch.org) database
  * A simple web server written with [Flask](http://flask.pocoo.org/) who responds to _JavaScript_ queries by fetching data in the _ElasticSearch_ database
  * A GUI written with [BootStrap](http://getbootstrap.com/) and [JQuery](http://jquery.com/)
