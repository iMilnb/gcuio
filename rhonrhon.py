#!/usr/bin/env python

import os
import sys
import irc.client
import irc.bot
import re
import datetime
import json
import logging
import hashlib
import signal
from logging.handlers import RotatingFileHandler
from elasticsearch import Elasticsearch
from threading import Thread
from twython import TwythonStreamer
from daemonize import Daemonize

# ~/.rhonrhonrc example
#
# name = "rhonrhon"
# pid = "/some/path/{0}.pid".format(name)
# logfile = "/some/path/{0}.log".format(name)
# logsize = 10000000 # 10M
# logrotate = 7 # 7 backups
#
# server = "chat.freenode.net"
# port = 6667
# channels = [ '#mychan' ]
# nickname = "mynick"
# nickpass = "my pass"
# realname = "Me, really"
# quit_message = "Seeya"
#
# es_nodes = [{'host': 'localhost'}]
# es_idx = "my_index"
#
# auth = {'opnick': {'passwd': 'sha256hash', 'twitter': True}}'
# # the previous sha256 hash can be simply obtained via:
# # print(hashlib.sha256("mysecretpassword".encode("utf-8")).hexdigest())'
#
# APP_KEY = "twitter_app_api_key"
# APP_SECRET = "twitter_app_api_secret"
# OAUTH_TOKEN = "twitter_oauth_token"
# OAUTH_TOKEN_SECRET = "twitter_oauth_token_secret"
#
# twichans = { '#mychan': 'MyTrack', '#otherchan': 'AnotherTrack' }

exec(open(os.path.expanduser("~") + '/.rhonrhonrc').read())

es = Elasticsearch(es_nodes)

# Lazy global
tweetrelay = True


class TwiStreamer(TwythonStreamer):

    ircbot = None

    def on_success(self, data):
        if 'text' in data:
            if self.ircbot is None:
                logger.info(data['text'].encode('utf-8'))
            elif tweetrelay is True and not 'retweeted_status' in data:
                for k in twichans:
                    # found matching text
                    if re.search(twichans[k], data['text']):
                        s = data['user']['screen_name']
                        n = data['user']['name']
                        out = '<@{0} ({1})> {2}'.format(s, n, data['text'])

                        self.ircbot.privmsg(k, out)

    def on_error(self, status_code, data):
        loggin.warn(status_code, data)


class CustomLineBuffer(irc.client.LineBuffer):
    def lines(self):
        ld = []
        for line in super(CustomLineBuffer, self).lines():
            try:
                ld.append(line.decode('utf-8', errors='strict'))
            except UnicodeDecodeError:
                ld.append(line.decode('iso-8859-15', errors='replace'))
        return iter(ld)


class Bot(irc.bot.SingleServerIRCBot):
    def __init__(self):
        self.auth = []
        self.t = None  # Twitter thread
        self.stream = None
        self.chaninfos = {}
        signal.signal(signal.SIGINT, self._signal_handler)
        # SIGTERM is handled by daemonize

        irc.client.ServerConnection.buffer_class = CustomLineBuffer
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)],
                                            nickname, realname)

    def _signal_handler(self, signal, frame):
        logger.info('quietly dying...')
        self.die(quit_message)

    def _dump_data(self, data, idx, doc_type):
        try:
            logger.info("dumping {0} to {1}/{2}".format(data,
                                                        es_idx,
                                                        doc_type))
        except UnicodeEncodeError:
            logger.warn("Your charset does not permit to dump that dataset.")

    def on_privnotice(self, serv, ev):
        logger.info("notice: {0}".format(ev.arguments[0]))
        source = ev.source.nick
        if source and source.lower() == 'nickserv':
            if re.search('identify', ev.arguments[0], re.I):
                self.connection.privmsg(source,
                                        'identify {0}'.format(nickpass))
            if re.search('identified', ev.arguments[0], re.I):
                self.chanjoin(serv)

    def chanjoin(self, serv):
        for chan in channels:
            logger.info("joining {0}".format(chan))
            serv.join(chan)

    def on_kick(self, serv, ev):
        self.chanjoin(serv)

    def on_pubmsg(self, serv, ev):
        nick = ev.source.nick
        full_date = datetime.datetime.utcnow()
        pl = ev.arguments[0]

        if (re.search('[\[#]\ *nolog\ *[#\]]', pl, re.I)) or 'nolog' in nick:
            return

        date, clock = full_date.isoformat().split('T')
        clock = re.sub('\.[0-9]+', '', clock)
        channel = ev.target.replace('#', '')

        tags = []
        tagmatch = '\s+#[^#]+#'
        tagsubs = re.findall(tagmatch, pl)
        for tagsub in tagsubs:
            tags += map(lambda x: x.strip(' '), tagsub.strip(' #').split(','))
            pl = re.sub(tagmatch, ' ', pl).rstrip(' ')

        urls = re.findall('(https?://[^\s]+)', pl)

        has_nick = False
        tonick = []
        tomatch = '^\ *([^:]+)\ *:\ *'
        tosub = re.search(tomatch, pl)
        if tosub and not re.search('https?', tosub.group(1)):
            for t in tosub.group(1).replace(' ', '').split(','):
                for ch in self.channels.keys():
                    if self.channels[ch].has_user(t) and ch == '#' + channel:
                        tonick.append(t)
                        has_nick = True

            if has_nick:
                pl = re.sub(tomatch, '', pl)

        data = {
            'fulldate': full_date.isoformat(),
            'date': date,
            'time': clock,
            'channel': channel,
            'server': serv.server,
            'nick': nick,
            'tonick': tonick,
            'tags': tags,
            'urls': urls,
            'line': pl
        }
        self._dump_data(data, es_idx, channel)

        r = es.index(index=es_idx, doc_type=channel, body=json.dumps(data))
        logger.debug(r)

    def on_privmsg(self, serv, ev):
        pl = ev.arguments[0]
        s = pl.split(' ')
        if not ev.source.nick in auth.keys():
            return
        if len(s) > 1 and s[0] == 'auth' and ev.source.nick in auth:
            h = hashlib.sha256(s[1].encode('utf-8')).hexdigest()
            nauth = auth[ev.source.nick]  # I don't exceed 80 cols.
            if 'passwd' in nauth and h == nauth['passwd']:
                self.auth.append(ev.source.nick)
                serv.notice(ev.source.nick, 'You are now authenticated')
        if not ev.source.nick in self.auth:
            return
        self.do_cmd(serv, s)

    def start_track(self, serv):
        self.stream = TwiStreamer(APP_KEY, APP_SECRET,
                                  OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
        self.stream.ircbot = serv
        target = ','.join(twichans.values())
        self.stream.statuses.filter(track=target)

    def do_cmd(self, serv, cmd):
        global tweetrelay
        logger.info(cmd[0])
        if cmd[0] == 'die':
            logger.info('je mata!')
            self.die(quit_message)
        if cmd[0] == 'join' and len(cmd) > 1:
            serv.join(cmd[1])
        if cmd[0] == 'part' and len(cmd) > 1:
            serv.part(cmd[1])
        if cmd[0] == 'twitter' and len(cmd) > 1:
            if cmd[1] == 'on':
                if self.t is None:
                    self.t = Thread(target=self.start_track, args=(serv,))
                    self.t.daemon = True
                    self.t.start()

                tweetrelay = True
            # shut twitter relay's mouth
            if cmd[1] == 'off' and self.t is not None:
                tweetrelay = False

    ### channel informations
    def _es_chaninfos(self, target):
        chan = target.replace('#', '')
        doc_type = '{0}_infos'.format(chan)
        date = datetime.datetime.utcnow().isoformat()

        data = {
            'date': date,
            'channel': chan,
            'topic': self.chaninfos[target]['topic'],
            'users': list(self.chaninfos[target]['users']),
            'ops': list(self.chaninfos[target]['ops'])
        }
        self._dump_data(data, es_idx, doc_type)

        r = es.index(index=es_idx, doc_type=doc_type, body=json.dumps(data))
        logger.debug(r)

    def _init_chaninfos(self, target):
        if not target in self.chaninfos:
            self.chaninfos[target] = {'topic': '', 'users': [], 'ops': []}

    def _refresh_chaninfos(self, target):
        if target and target.startswith('#'):
            self._init_chaninfos(target)
            self.chaninfos[target]['users'] = self.channels[target].users()
            self.chaninfos[target]['ops'] = self.channels[target].opers()
            self._es_chaninfos(target)

    def _refresh_all_chans(self):
        for k in self.chaninfos:
            self._refresh_chaninfos(k)

    def on_currenttopic(self, serv, ev):
        self._init_chaninfos(ev.arguments[0])
        self.chaninfos[ev.arguments[0]]['topic'] = ev.arguments[1]
        self._refresh_chaninfos(ev.arguments[0])

    def on_topic(self, serv, ev):  # force refresh currenttopic
        serv.topic(ev.target)

    def on_join(self, serv, ev):
        self._refresh_chaninfos(ev.target)

    def on_part(self, serv, ev):
        self._refresh_chaninfos(ev.target)

    def on_quit(self, serv, ev):
        self._refresh_all_chans()  # quit doesn't set any target


foreground = False

# mainly copypasta from
# https://github.com/thesharp/daemonize
# http://sametmax.com/ecrire-des-logs-en-python/

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(message)s')

if '-f' in sys.argv:
    foreground = True
    fh = logging.StreamHandler(sys.stdout)
else:
    fh = RotatingFileHandler(logfile, 'a', logsize, logrotate)
    keep_fds = [fh.stream.fileno()]

fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

# instanciate the bot
b = Bot()

if foreground is False:
    daemon = Daemonize(app=name,
                       pid=pid,
                       action=b.start,
                       keep_fds=keep_fds)
    daemon.start()

elif __name__ == '__main__':
    b.start()
