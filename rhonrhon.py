#!/usr/bin/env python
 
from __future__ import unicode_literals

import irc.client
import irc.bot
import re
import datetime
import json
import requests
from os.path import expanduser

# inspired from
# http://fr.wikibooks.org/wiki/D%C3%A9butez_dans_IRC/Cr%C3%A9er_un_robot
# http://svn.red-bean.com/repos/ircbots/trunk/beanbot.py

execfile(expanduser("~") + '/.rhonrhonrc')

# from http://code.activestate.com/recipes/466341-guaranteed-conversion-to-unicode-or-byte-string/
def safe_unicode(obj, *args):
    """ return the unicode representation of obj """
    try:
        return unicode(obj, *args)
    except UnicodeDecodeError:
        ascii_text = str(obj).decode('ISO-8859-15', errors='replace')
        return unicode(ascii_text)

class Bot(irc.bot.SingleServerIRCBot):
    def __init__(self):
        self.auth = []
        irc.client.ServerConnection.buffer_class = irc.buffer.LineBuffer
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)],
                                           nickname, realname)

    def on_privnotice(self, serv, ev):
        print "notice: {0}".format(ev.arguments[0])
        source = ev.source.nick
        if source and source.lower() == 'nickserv':
            if re.search(r'identify', ev.arguments[0], re.I):
                self.connection.privmsg(source, 'identify {0}'.format(nickpass))
            if re.search(r'identified', ev.arguments[0], re.I):
                self.chanjoin(serv)

    def chanjoin(self, serv):
        for chan in channels:
            print "joining {0}".format(chan)
            serv.join(chan)

    def on_kick(self, serv, ev):
        self.chanjoin(serv)

    def on_pubmsg(self, serv, ev):
        pl = safe_unicode(ev.arguments[0]).encode('utf-8')
        if (re.search(r'[\[#]\ *nolog\ *[#\]]', pl, re.I)):
            return

        tags = []
        tagmatch = r'#\ *([^#]+)\ *#'
        tagsub = re.search(tagmatch, pl)
        if tagsub:
            tags = tagsub.group(1).replace(' ', '').split(',')
            pl = re.sub(tagmatch, '', pl)

        urls = re.findall(r'(https?://[^\s]+)', pl)

        tonick = []
        tomatch = r'^\ *([^:]+)\ *:\ *'
        tosub = re.search(tomatch, pl)
        if tosub:
            tonick = tosub.group(1).replace(' ', '').split(',')
            pl = re.sub(tomatch, '', pl)

        date, clock = datetime.datetime.utcnow().isoformat().split('T')
        channel = ev.target.replace('#', '')

        data = {
            'fulldate': datetime.datetime.utcnow().isoformat(),
            'date': date,
            'time': clock,
            'channel': channel,
            'server': serv.server,
            'nick': ev.source.nick,
            'tonick': tonick,
            'tags': tags,
            'urls': urls,
            'line': pl
        }
        es_idx = "{0}/{1}/".format(es_url, channel)
        print "dumping {0} to {1}".format(data, es_idx)
        r = requests.post(es_idx, json.dumps(data))
        print r.json()

    def on_privmsg(self, serv, ev):
        pl = safe_unicode(ev.arguments[0]).encode('utf-8')
        s = pl.split(' ')
        if not ev.source.nick in auth.keys():
            return
        if len(s) > 1 and s[0] == u'auth' and s[1] == auth[ev.source.nick]:
            self.auth.append(ev.source.nick)
            serv.notice(ev.source.nick, u'You are now authenticated')
        if not ev.source.nick in self.auth:
            return
        self.do_cmd(serv, s)

    def do_cmd(self, serv, cmd):
        print cmd
        if cmd[0] == u'die':
            self.die()
        if cmd[0] == u'join' and cmd > 1:
            serv.join(cmd[1])
        if cmd[0] == u'part' and cmd > 1:
            serv.part(cmd[1])

if __name__ == "__main__":
    Bot().start()
