#!/usr/bin/env python

import os
import re
import getopt
import sys
import socket
import time
from os.path import expanduser

# FIXME: adapt to your file tree
logdir=expanduser("~") + '/gcu'

server='irc.freenode.org'

# The next regex should allow the script to extract the channel and the full
# date of the log file (each element of the full-date will be passed to a
# function you can overwrite later) please make sure each matching element is
# accessible from a dict (eg: dict['channel'], dict['day'], dict['month'],
# dict['year'])
file_name_match = '(?P<channel>[^.]+)\.log\.(?P<day>\d{1,2})(?P<month>\w{3})(?P<year>\d{4})'

port = 0

class myDate:

    def __init__(self, year, month, day):
        self.date_format = { 'day'  : lambda d: int(d)
                           ,'month': lambda d: self.format_month(d)
                           ,'year' : lambda d: int(d)
                          }

        self.months = { 'Jan': 1
                  ,'Feb': 2
                  ,'Mar': 3
                  ,'Apr': 4
                  ,'May': 5
                  ,'Jun': 6
                  ,'Jul': 7
                  ,'Aug': 8
                  ,'Sep': 9
                  ,'Oct': 10
                  ,'Nov': 11
                  ,'Dec': 12
                 }

        self.year =  self.date_format['year'](year)
        self.month = self.date_format['month'](month)
        self.day =   self.date_format['day'](day)

    def format_month(self, month):
        return self.months[month]

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return str(self.year) + "/" + str(self.month) + "/" + str(self.day)

    def toRhonrhon(self):
        return str(self.year) + " " + str(self.month) + " " + str(self.day)


def walk_dir(logdir):
    for dirname, dirnames, filenames in os.walk(logdir):
        for subdirname in dirnames:
            walk_dir(subdirname)

        for filename in filenames:
            read_log_file(filename)

def read_log_file(filename):
    tomatch = re.search(file_name_match, filename)
    if not tomatch:
        print 'error parsing filename {0}'.format(filename)
        return
    m_dict = tomatch.groupdict()

    date = myDate(m_dict['year'], m_dict['month'], m_dict['day'])

    print "notice: channel={0}, full-date=({1})".format(m_dict['channel'], date)

    s = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", port))

    #FIXME: don't set channel/server at every files
    set_rhonrhon_attrs(s, 'channel', m_dict['channel'])
    set_rhonrhon_attrs(s, 'server', server)
    set_rhonrhon_attrs(s, 'date' , date.toRhonrhon())

    time.sleep(0.1)

    f = open(filename, 'r')
    for line in f:
        if re.search('<[^>]+>', line):
            print line
            s.send(line)
            s.recv(1)

    s.close()



def set_rhonrhon_attrs(s, key, item):
    s.send(key + "=" + item + "\n")

def _usage():
    print "Usage: {0} -p 1337".format(sys.argv[0])

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hp:')
    except getopt.GetoptError:
        _usage()
    for opt, arg in opts:
        if opt == '-h':
            _usage()
            sys.exit()
        elif opt == "-p":
            port = int(arg)
    if port > 0:
        walk_dir(logdir)
    else:
        _usage()



