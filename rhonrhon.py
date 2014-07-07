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
from twython import Twython
from twython import TwythonStreamer
from twython import TwythonError, TwythonRateLimitError, TwythonAuthError
from daemonize import Daemonize

import rhonmod.coin

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


def has_expected_mode(path, mode):
    from stat import S_IMODE
    st = os.stat(path)
    return S_IMODE(st.st_mode) == mode

configFile = os.path.expanduser("~") + '/.rhonrhonrc'
if not has_expected_mode(configFile, 0o600):
    print("err: invalid mode on configFile, should be 600", configFile)
    sys.exit(2)

exec(open(configFile).read())

es = Elasticsearch(es_nodes)

# Lazy global
tweetrelay = True


class TwiStreamer(TwythonStreamer):

    ircbot = None

    TWEET_TEXT_REPLACE = {
        '\n': ' ',
        '&lt;': '<',
        '&gt;': '>',
    }

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
                        t = data['text']
                        for text, repl in self.TWEET_TEXT_REPLACE.items():
                            t = t.replace(text, repl)
                        out = '<@{0} ({1})> {2}'.format(s, n, t)
                        out = out[0:512]

                        self.ircbot.privmsg(k, out)

    def on_error(self, status_code, data):
        logger.warn(status_code, data)


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
        self._registered_users = []
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

    def _user_register(self, nickmask):
        if not(nickmask in self._registered_users):
            self._registered_users.append(nickmask)

    def _user_unregister(self, nickmask):
        if nickmask in self._registered_users:
            self._registered_users.remove(nickmask)

    def _user_is_registered(self, nickmask):
        return nickmask in self._registered_users

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

    def showmsg(self, serv, ev, t, line):
        if t == 'pub':
            serv.privmsg(ev.target, line)
        if t == 'priv':
            serv.notice(ev.source.nick, line)

    def showrage(self, serv, ev, t):
        if 'ragedir' in globals():
            ragefaces = []
            for r, d, files in os.walk(ragedir):
                for f in files:
                    ragefaces.append(re.sub('\.(jpe?g|png|gif|svg)', '', f))
            if ragefaces:
                ragefaces.sort(reverse=True)
                l = 0
                curline = ''
                rarr = []
                while len(ragefaces) > 0:
                    rage = ragefaces.pop()
                    if len(curline) + len(rage) < 450:
                        rarr.append(rage)
                        curline = ', '.join(rarr)
                    else:
                        self.showmsg(serv, ev, t, curline)
                        curline = rage
                        rarr = [rage]

                self.showmsg(serv, ev, t, ', '.join(rarr))

    def showcoin(self, serv, ev, t):
        args = ev.arguments[0].strip().split(' ')
        self.showmsg(serv, ev, t, rhonmod.coin.reply(args))

    def handle_pubcmd(self, serv, ev):
        '''
        Handle public IRC bot-style commands e.g. !foo
        '''
        pl = ev.arguments[0].strip()
        nickauth = {}
        # nick is registered, get it's auth dict entry in conf file
        if self._user_is_registered(ev.source):
            nickauth = auth[ev.source.nick]

        # public tweets
        match = re.search('^!tweet\s(.*)$', pl, re.I)
        if match:
            if 'twitter' in nickauth and nickauth['twitter'] is True:
                msg = match.group(1)
                if (len(msg) > 140):
                    serv.privmsg(ev.target, "too long.")
                    return
                twitter = Twython(APP_KEY,
                                  APP_SECRET,
                                  OAUTH_TOKEN,
                                  OAUTH_TOKEN_SECRET)
                try:
                    data = twitter.update_status(status=msg)
                    s = data['user']['screen_name']
                    i = data['id']
                    out = 'Status updated: https://twitter.com/{0}/status/{1}'
                    out = out.format(s, i)
                    serv.privmsg(ev.target, out)
                    logger.info(ev.source.nick + " updated twitter: " + msg)
                except TwythonAuthError:
                    logger.warn("twitter: can't authenticate")
            else:
                serv.privmsg(ev.target, "no.")
            # return True anyway as we don't want to record that line
            return True

        # output all available ragefaces
        if pl.startswith('!rage'):
            self.showrage(serv, ev, 'pub')
            return True

        # output coin values
        if pl.startswith('!coin'):
            self.showcoin(serv, ev, 'pub')
            return True

        # not a known command
        return False

    def on_pubmsg(self, serv, ev):
        nick = ev.source.nick.strip()
        full_date = datetime.datetime.utcnow()
        pl = ev.arguments[0].strip()

        if (re.search('[\[#]\ *nolog\ *[#\]]', pl, re.I)) or 'nolog' in nick:
            return

        # stop logging pinpin's "foo runne <irc client>"
        if nick.startswith('pinpin') and re.search('runne ', pl):
            return

        # handle !commands
        if pl.startswith('!') and self.handle_pubcmd(serv, ev) is True:
            return

        # handle regular irc lines
        date, clock = full_date.isoformat().split('T')
        clock = re.sub('\.[0-9]+', '', clock)
        channel = ev.target.replace('#', '')

        tags = []
        tagmatch = '\s+#[^#]+#'
        tagsubs = re.findall(tagmatch, pl)
        for tagsub in tagsubs:
            tags += map(lambda x: x.strip(' '), tagsub.strip(' #').split(','))
            pl = re.sub(tagmatch, ' ', pl).rstrip(' ')

        if 'nolog' in tags:
            return

        urls = re.findall('(https?://[^\s]+)', pl)
        urls_copy = list(urls)
        for url in urls_copy:
            (vieille, rep) = self.vieille(url, channel)
            if vieille:
                try:
                    msg = '{0}: VIEUX ! The URL [ {1} ] has been posted '
                    msg = msg + 'by {2} the {3} at {4}.'

                    if len(msg) > 512:
                        msg = '{0}: VIEUX ! This URL has been posted '
                        msg = msg + 'by {2} the {3} at {4}.'

                    serv.privmsg('#{0}'.format(channel),
                                 msg.format(nick,
                                            url,
                                            'you' if rep['_source']['nick'] == nick
                                            else rep['_source']['nick'],
                                            rep['_source']['date'],
                                            rep['_source']['time']))
                except Exception as e:
                    logger.warn(e)
                    pass

                urls.remove(url)

        has_nick = False
        tonick = []
        tomatch = '^\ *([^:]+)\ *:\ *'
        tosub = re.search(tomatch, pl)
        if tosub and not re.search('https?', tosub.group(1)):
            for t in tosub.group(1).replace(' ', '').split(','):
                if t != '':
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

    def handle_noauth_privcmd(self, serv, ev, s):
        if s[0] == 'rage':
            self.showrage(serv, ev, 'priv')
            return True

        # Ask rhonrhon weither a list of URLs are old or not.
        # Syntax: urls?:? (#channel)? text containing URLs.
        # The default channel is #gcu.
        # Ex: url: #gcu c'est bon la rhonrhon ? https://www.google.com
        # Ex: urls http://www.bonjourmadame.fr ou alors
        # http://bonjourlesroux.tumblr.com
        if re.match('^urls?:?$', s[0]):
            i = 1
            if re.match('^#.*$', s[1]):
                channel = s[1].replace('#', '')
                i += 1
            else:
                channel = 'gcu'

            for url in [x for x in s[i:] if re.match('(https?://[^\s]+)', x)]:
                if len(url) > 262:
                    msg = 'SAYTROPLONG [ {0} ]'
                else:
                    (vieille, rep) = self.vieille(url, channel)
                    if vieille:
                        msg = 'VIEUX ! [ {0} ]'
                    else:
                        msg = 'SAYBON  [ {0} ]'
                serv.privmsg(ev.source.nick, msg.format(url))
            return True

        return False

    def on_privmsg(self, serv, ev):
        pl = ev.arguments[0]
        s = pl.split(' ')
        if not s:
            return  # no command passed (is it even possible ? :) )
        if self.handle_noauth_privcmd(serv, ev, s) is True:
            return  # a publicly accessible command was provided
        if not ev.source.nick in auth.keys():
            return
        if len(s) > 1 and s[0] == 'auth' and ev.source.nick in auth:
            h = hashlib.sha256(s[1].encode('utf-8')).hexdigest()
            nauth = auth[ev.source.nick]  # I don't exceed 80 cols.
            if 'passwd' in nauth and h == nauth['passwd']:
                self._user_register(ev.source)
                serv.notice(ev.source.nick, 'You are now authenticated')
        if not self._user_is_registered(ev.source):
            return
        self.do_cmd(serv, s)

    def start_track(self, serv):
        try:
            self.stream = TwiStreamer(APP_KEY, APP_SECRET,
                                      OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
            self.stream.ircbot = serv
            target = ','.join(twichans.values())
            self.stream.statuses.filter(track=target)
        except Exception as e:
            logger.warn(e)

            # mark twitter as not disable
            tweetrelay = False

            # cleanup thread in order to be able to restart
            self.t = None

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
        self._user_unregister(ev.source)

    def on_quit(self, serv, ev):
        self._refresh_all_chans()  # quit doesn't set any target
        self._user_unregister(ev.source)

    def vieille(self, url, channel):
        urlbody = {
            'query': {
                'match_phrase': {'urls': url}
                },
            'size': 1
            }
        try:
            res = es.search(index=es_idx, doc_type=channel, body=urlbody)
            for rep in res['hits']['hits']:
                return (True, rep)
        except Exception as e:
            logger.warn(e)
            pass
        return (False, [])



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
