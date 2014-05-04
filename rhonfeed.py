#!/usr/bin/env python

import os
import sys
import re
import random
import string
import json
from elasticsearch import Elasticsearch, helpers

server = 'chat.freenode.net'
channel = 'gcu'
es_idx = 'rhonrhon'

numonth = {
    'Jan': '01',
    'Feb': '02',
    'Mar': '03',
    'Apr': '04',
    'May': '05',
    'Jun': '06',
    'Jul': '07',
    'Aug': '08',
    'Sep': '09',
    'Oct': '10',
    'Nov': '11',
    'Dec': '12',
}

ircline = '\[(\d{2}:\d{2})\]\s+<([^\>]+)>\s+(.+)'

es = Elasticsearch()

def process_ircline(hdate, time, nick, pl):
    if (re.search('[\[#]\ *nolog\ *[#\]]', pl, re.I)) or 'nolog' in nick:
        return

    date = '{0}-{1}-{2}'.format(hdate['year'], hdate['month'], hdate['day'])
    if re.search('^\d{2}:\d{2}$', time):
        time = '{0}:00'.format(time)
    clock = time

    tags = []
    tagmatch = '#\ *([^#]+)\ *#\s*'
    tagsub = re.search('\ ' + tagmatch, pl)
    if tagsub:
        tags = tagsub.group(1).replace(' ', '').split(',')
        pl = re.sub(tagmatch, '', pl)

    urls = re.findall('(https?://[^\s]+)', pl)

    has_nick = False
    tonick = []
    tomatch = '^([^:\ ]+):\ *'
    tosub = re.search(tomatch, pl)
    if tosub and not re.search('https?', tosub.group(1)):
        for t in tosub.group(1).replace(' ', '').split(','):
            tonick.append(t)
            has_nick = True

        if has_nick:
            pl = re.sub(tomatch, '', pl)

    rnd = ''.join([random.choice(string.digits) for n in range(6)])
    data = {
        'fulldate': '{0}T{1}.{2}'.format(date, clock, rnd),
        'date': date,
        'time': clock,
        'channel': channel,
        'server': server,
        'nick': nick,
        'tonick': tonick,
        'tags': tags,
        'urls': urls,
        'line': pl
    }
    return data

def process_file(filename, date):
    with open(filename) as logfile:
        print('processing {0}'.format(filename))
        bulk = []
        for line in logfile:
            r = re.search(ircline, line.rstrip())
            if r:
                time = r.group(1)
                nick = r.group(2)
                pl = r.group(3)
                source = process_ircline(date, time, nick, pl)
                action = {
                    '_index': es_idx,
                    '_type': channel,
                    '_source': source
                }
                bulk.append(action)

        helpers.bulk(es, bulk)

def walkdir(logdir):
    for root, dirs, files in os.walk(logdir):
        for name in files:
            f = re.search('^gcu\.log\.(\d{1,2})(\w{3})(\d{4})', name)
            if f:
                f_date = {
                    'day':  f.group(1),
                    'month': numonth[f.group(2)],
                    'year': f.group(3)
                }

                process_file(os.path.join(root,name), f_date)

if __name__ == '__main__' and len(sys.argv) > 1:
    walkdir(sys.argv[1])
