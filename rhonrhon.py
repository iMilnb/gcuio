#!/usr/bin/env python

import irc.client
import irc.bot
import re
import datetime
import json
import requests
import getopt
import sys
import socket
import thread
from os.path import expanduser

exec(open(expanduser("~") + '/.rhonrhonrc').read())

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

        if listen_port > 0:
            print "Creating listening socket on 127.0.0.1:{0} to get fed !".format(listen_port)
            server_thread = thread.start_new_thread(self.create_server_socket, (int(listen_port),))

        irc.client.ServerConnection.buffer_class = CustomLineBuffer
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)],
                                           nickname, realname)

    def on_privnotice(self, serv, ev):
        print("notice: {0}".format(ev.arguments[0]))
        source = ev.source.nick
        if source and source.lower() == 'nickserv':
            if re.search('identify', ev.arguments[0], re.I):
                self.connection.privmsg(source, 'identify {0}'.format(nickpass))
            if re.search('identified', ev.arguments[0], re.I):
                self.chanjoin(serv)

    def chanjoin(self, serv):
        for chan in channels:
            print("joining {0}".format(chan))
            serv.join(chan)

    def on_kick(self, serv, ev):
        self.chanjoin(serv)

    def on_pubmsg(self, serv, ev):
        self._handle_on_pubmsg(serv.server, ev.source.nick, ev.target, datetime.datetime.utcnow().isoformat(), ev.arguments[0])

    def _handle_on_pubmsg(self, serv, nick, target, full_date, pl):
        """Handle on_pubmsg event.

        Arguments:

            serv  -- The server from which we received the event

            nick  -- The nick of the sender

            target -- Receiver of the message

            full_date -- The date when the message was received

            pl  -- Content of the message

        This method should be called to handle a pub_msg received from
        a real IRC server or from a client socket
        """

        if (re.search('[\[#]\ *nolog\ *[#\]]', pl, re.I)):
            return

        date, clock = full_date.split('T')
        clock = re.sub('\.[0-9]+', '', clock)
        channel = target.replace('#', '')

        tags = []
        tagmatch = '#\ *([^#]+)\ *#'
        tagsub = re.search(tagmatch, pl)
        if tagsub:
            tags = tagsub.group(1).replace(' ', '').split(',')
            pl = re.sub(tagmatch, '', pl)

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
            'fulldate': full_date,
            'date': date,
            'time': clock,
            'channel': channel,
            'server': serv,
            'nick': nick,
            'tonick': tonick,
            'tags': tags,
            'urls': urls,
            'line': pl
        }
        es_idx = "{0}/{1}/".format(es_url, channel)
        try:
            print("dumping {0} to {1}".format(data, es_idx))
        except UnicodeEncodeError:
            print("Your charset does not permit to dump that dataset.")

        r = requests.post(es_idx, json.dumps(data))
        print(r.json())

    def on_privmsg(self, serv, ev):
        pl = ev.arguments[0]
        s = pl.split(' ')
        if not ev.source.nick in auth.keys():
            return
        if len(s) > 1 and s[0] == 'auth' and s[1] == auth[ev.source.nick]:
            self.auth.append(ev.source.nick)
            serv.notice(ev.source.nick, 'You are now authenticated')
        if not ev.source.nick in self.auth:
            return
        self.do_cmd(serv, s)

    def do_cmd(self, serv, cmd):
        print(cmd)
        if cmd[0] == 'die':
            self.die(quit_message)
        if cmd[0] == 'join' and len(cmd) > 1:
            serv.join(cmd[1])
        if cmd[0] == 'part' and len(cmd) > 1:
            serv.part(cmd[1])

    def create_server_socket(self, listen_port):
        self.serv_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
        self.serv_socket.bind(('127.0.0.1', listen_port))
        self.serv_socket.listen(1)
        #TODO: handle multiple clients at a time
        self.readIRCFeed()

    def readIRCFeed(self):
        (client_socket, address) = self.serv_socket.accept()
        try:
            data = client_socket.recv(1024)
            while len(data) > 0:
                data = data.rstrip('\n')
                print "data=({0})".format(data)
                self._handle_on_pubmsg(server, 'nick_test', '#gcu', datetime.datetime.utcnow().isoformat(), data)
                data = client_socket.recv(1024)
        except socket.error, e:
            sys.exit(0)
        finally:
            self.serv_socket.close()

if __name__ == "__main__":
    listen_port = 0
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:hl:s:')
    except getopt.GetoptError:
        Bot().start()
    for opt, arg in opts:
        if opt == '-h':
            print "{0} -h [ -l 1337 ]".format(sys.argv[0])
            sys.exit()
        elif opt == "-l":
            listen_port = arg
    Bot().start()
