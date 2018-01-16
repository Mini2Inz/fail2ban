# coding: utf-8
__author__    = u"Radosław Dąbrowski"
__copyright__ = u"Copyright (c) 2017 Radosław Dąbrowski"
__license__   = u"GPL"

import os
import socket, asyncore, asynchat
import shlex
from pprint import pformat
from ..helpers import getLogger
from ticket import Ticket

HOSTSFILE = "hosts"
ADDR      = ""
PORT      = 12345
BACKLOG   = 5

# Gets the instance of the logger.
logSys = getLogger(__name__)

# Useful links:
#   - asyncore.dispatcher: https://docs.python.org/2/library/asyncore.html#asyncore-example-basic-echo-server
#   - asynchat.async_chat: https://docs.python.org/2/library/asynchat.html#module-asynchat


def xstr(x):
    if x is None:
        return ''
    else:
        return str(x)


class ShareServer(asyncore.dispatcher):

    def __init__(self, server, conf, addr = ADDR, port = PORT, backlog = BACKLOG):
        asyncore.dispatcher.__init__(self)
        self._server = server
        self._conf = conf
        logSys.debug("Received conf:\n%s", pformat(conf))
        self._hosts = []
        self.readHosts(conf.get('sharehosts'))
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self._port = conf.get('shareport', port)
        self.bind((addr, self._port))
        self.listen(BACKLOG)
        logSys.debug("ShareServer is listening on %s:%d", addr, self._port)

    def readHosts(self, hosts, filename = HOSTSFILE):
        def add_host(configline):
            try:
                addr, port = configline.strip().split(':')
                self._hosts.append((addr, int(port)))
            except:
                logSys.warning("Failed to process line: %s", configline)

        if not hosts:
            filename = os.path.join(self._conf.get("conf"), filename)
            logSys.debug("Reading hosts from file %s...", filename)
            if os.path.isfile(filename):
                with open(filename) as f:
                    for line in f.readlines():
                        add_host(line)
            else:
                logSys.warning("No hosts file")
        else:
            for host in hosts.split('\n'):
                add_host(host.strip())

        logSys.debug("Share hosts:\n%s", pformat(self._hosts))

    def handle_accept(self):
        client = self.accept()
        if client is not None:
            sock, (addr, port) = client
            logSys.debug("Incoming connection from %s:%d", addr, port)
            handler = CommandHandler(self._server, sock, addr, port)

    def shareTicket(self, jail, ticket):
        logSys.debug("Sharing ticket %s from jail %s...", ticket.getIP(), jail)
        for host in self._hosts:
            addr, port = host
            client = ShareClient(jail, ticket, addr, port)


class CommandHandler(asynchat.async_chat):

    def __init__(self, server, sock, addr, port):
        asynchat.async_chat.__init__(self, sock=sock)
        self._server = server
        self._addr = addr
        self._port = port
        self._buffer = []
        self.set_terminator("\n")
        logSys.debug("Created CommandHandler for %s:%d", addr, port)

    def collect_incoming_data(self, data):
        self._buffer.append(data)

    def found_terminator(self):
        msg = "".join(self._buffer)
        self._buffer = []
        logSys.debug("Received message from %s:%d: %s", \
            self._addr, self._port, msg)
        tokens = shlex.split(msg)
        cmd, args = tokens[0], tokens[1:]
        logSys.debug("Command %s with arguments: %s", \
            cmd, ", ".join(args))
        if cmd == "BANIP":
            self._recv_ban(args)
        elif cmd == "BANS":
            self._send_bans(args)
        elif cmd == "LOCATIONS":
            self._send_locations(args)
        else:
            self.push("Unknown command {}\n\n".format(cmd))

    def _recv_ban(self, args):
        # Parse args
        if (len(args) == 3):
            jailname, ip, timeofban = args
            bantime = None
        elif (len(args) == 4):
            jailname, ip, timeofban, bantime = args
        else:
            self.push("Incorrect arguments.\n")
            self.push("Usage: BANIP <jail> <ip> <timeofban> [bantime]\n\n")
            return
        # Create ticket
        ticket = Ticket(ip, float(timeofban))
        ticket.external = True
        if (bantime is not None):
            ticket.setBanTime(bantime)
        # Put ticket into a jail
        if self._server.getJails().exists(jailname):
            logSys.debug("Putting ticket into the jail %s...", jailname)
            jail = self._server.getJails()[jailname]
            jail.putFailTicket(ticket)
        else:
            logSys.debug("No jail %s found. Ignoring...", jailname)
        # Send empty response
        self.push("\n")

    def _send_bans(self, args):
        bans = self._server.getDatabase().dumpBans()
        for ban in bans:
            self.push(",".join(map(xstr, ban)) + "\n")
        self.push("\n")

    def _send_locations(self, args):
        locations = self._server.getDatabase().dumpLocations()
        for loc in locations:
            self.push(",".join(map(xstr, loc)) + "\n")
        self.push("\n")


class ShareClient(asyncore.dispatcher):

    def __init__(self, jail, ticket, addr, port = PORT):
        asyncore.dispatcher.__init__(self)
        self._addr = addr
        self._port = port
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((addr, port))
        self.buffer = "BANIP {} {} {} {}\n".format(
            jail, ticket.getIP(), ticket.getTime(),
            ticket.getBanTime() if ticket.getBanTime() is not None else "")

    def handle_connect(self):
        logSys.debug("Connected to %s:%d.", \
            self._addr, self._port)

    def handle_error(self):
        logSys.warning("Error occured while trying to connect to %s:%d.", \
            self._addr, self._port)

    def handle_close(self):
        self.close()

    def handle_read(self):
        data = self.recv(8192)
        msg = data.decode('utf-8')
        logSys.debug("Received response from %s:%d: %s", \
            self._addr, self._port, msg)

    def writable(self):
        return (len(self.buffer) > 0)

    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]
