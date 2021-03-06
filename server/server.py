import pyev
import os
import sys
import logging
import socket
import signal
import errno

from register import register, post, get
from connection import Connection

STOPSIGNALS = (signal.SIGINT, signal.SIGTERM)
NONBLOCKING = (errno.EAGAIN, errno.EWOULDBLOCK)

class Server(object):

    def __init__(self, bind_host, handler):
        register.handler = handler
        self.bind_host = bind_host
        self.connections = {}
        self.loop = pyev.default_loop()
        self.watchers = [pyev.Signal(sig, self.loop, self.signal_cb)
                         for sig in STOPSIGNALS]
        # create the socket and bind
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(bind_host)
        self.sock.setblocking(0)
        # create the watcher that listens for new connections
        self.listen_watcher = pyev.Io(
            self.sock, pyev.EV_READ, self.loop, self.io_cb)

    def signal_cb(self, watcher, revents):
        self.stop()

    def stop(self):
        self.loop.stop(pyev.EVBREAK_ALL)
        while self.watchers:
            self.watchers.pop().stop()

    def reset(self, events):
        self.listen_watcher.stop()
        self.listen_watcher.set(self.sock, events)
        self.listen_watcher.start()

    def io_cb(self, watcher, revents):
        if revents & pyev.EV_READ:
            self.handle_connect()
        self.reset(pyev.EV_READ)

    def start(self):
        '''
            Start generic watchers and loop
        '''
        # start generic watchers        
        for watcher in self.watchers:
            watcher.start()
        self.sock.listen(socket.SOMAXCONN)
        self.listen_watcher.start()
        logging.debug("Server.start - starting server")
        self.loop.start()

    def handle_connect(self):
        try:
            sock, address = self.sock.accept()
        except socket.error as err:
            if err.args[0] in NONBLOCKING:
                pass
            else:
                logging.error(
                    "error [%s] accepting a connection" % err.args[1])    
        else:
            logging.info("Server.handle_connect - connection from %s:%d" % address)    
            conn = Connection(sock, self.loop, address)

if __name__ == '__main__' :
    
    from response import HttpResponse

    class Handler(object):
        
        def __init__(self):
            pass

        @post('/path/<name>/test')
        def foo(self, name, http_request):
            r = HttpResponse()
            r.headers['Host'] = 'localhost'
            r.headers['Content-Type'] = 'application/json'
            r.body = '{"status": %s}' % name
            return r
        
        @get('/path/<name>/test/<qualifier>')
        def bar(self, name, qualifier, http_request):
            r = HttpResponse()
            r.headers['Host'] = 'localhost'
            r.headers['Content-Type'] = 'application/json'
            r.body = '{"status": %s}' % qualifier
            return r

    h = Handler()
    s = Server(('127.0.0.1', 8989), h)
    s.start()

        
