__author__    = "Radosław Dąbrowski"
__copyright__ = "Copyright (c) 2017 Radosław Dąbrowski"
__license__   = "GPL"

import asyncore, socket
from ..helpers import getLogger

ADDR    = ''
PORT    = 1234
BACKLOG = 5

# Gets the instance of the logger.
logSys = getLogger(__name__)

# Useful links:
#   - asyncore.dispatcher: https://docs.python.org/2/library/asyncore.html#asyncore-example-basic-echo-server


class ShareServer(asyncore.dispatcher):

    def __init__(self, addr = ADDR, port = PORT, backlog = BACKLOG):
        asyncore.dispatcher.__init__(self)
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
