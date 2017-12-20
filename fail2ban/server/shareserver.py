__author__    = "Radosław Dąbrowski"
__copyright__ = "Copyright (c) 2017 Radosław Dąbrowski"
__license__   = "GPL"

import socket, asyncore, asynchat
import shlex
from ..helpers import getLogger

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
        self.push("Not implemented yet. Sorry...\n\n")

    def _send_bans(self, args):
        bans = self._server.getDatabase().dumpBans()
        for ban in bans:
            self.push(",".join(map(xstr, ban)) + "\n")
        self.push("\n")

    def _send_locations(self, args):
        self.push("Not implemented yet. Sorry...\n\n")
