__author__    = "Radosław Dąbrowski"
__copyright__ = "Copyright (c) 2017 Radosław Dąbrowski"
__license__   = "GPL"

import socket, asyncore, asynchat
import shlex
from ..helpers import getLogger
from ticket import Ticket

ADDR    = ''
PORT    = 1234
BACKLOG = 5

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

    def __init__(self, server, addr = ADDR, port = PORT, backlog = BACKLOG):
        asyncore.dispatcher.__init__(self)
        self._server = server
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((addr, port))
        self.listen(BACKLOG)
        logSys.debug("ShareServer is listening on %s:%d", addr, port)

    def handle_accept(self):
        client = self.accept()
        if client is not None:
            sock, (addr, port) = client
            logSys.debug("Incoming connection from %s:%d", addr, port)
            handler = CommandHandler(self._server, sock, addr, port)

    def shareTicket(self, jail, ticket):
        logSys.debug("Sharing ticket %s from jail %s...", ticket.getIP(), jail)
        client = ShareClient(jail, ticket, "172.17.0.1")

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
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((addr, port))
        self.buffer = "BANIP {} {} {} {}\n".format(
            jail, ticket.getIP(), ticket.getTime(),
            ticket.getBanTime() if ticket.getBanTime() is not None else "")

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def writable(self):
        return (len(self.buffer) > 0)

    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]
