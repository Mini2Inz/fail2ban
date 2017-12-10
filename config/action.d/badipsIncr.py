# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: t -*-
# vi: set ft=python sts=4 ts=4 sw=4 noet :

# This file is part of Fail2Ban.
#
# Fail2Ban is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Fail2Ban is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fail2Ban; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import sys

if sys.version_info < (2, 7):
    raise ImportError("badips.py action requires Python >= 2.7")
import json
import threading
import logging

if sys.version_info >= (3,):
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode
    from urllib.error import HTTPError
else:
    from urllib2 import Request, urlopen, HTTPError
    from urllib import urlencode

from fail2ban.server.actions import ActionBase


class BadIpsIncrBanTime(ActionBase):
    """
    Fail2Ban action which increments ban time if IP address
    is present in badips.com database.
    """
    TIMEOUT = 10
    _badips = "http://www.badips.com"

    def _Request(self, url, **argv):
        return Request(url, headers={'User-Agent': self.agent}, **argv)

    def __init__(self, jail, name, time_increment=None, agent="Fail2Ban", timeout=TIMEOUT):
        super(BadIpsIncrBanTime, self).__init__(jail, name)

        self._logSys.debug("__init__: timeout %s time_increment %s",
                           str(timeout), str(time_increment))
        self.timeout = int(timeout)
        self.time_increment = int(time_increment)
        self.agent = agent

        self._banned_ips = set()

    @staticmethod
    def isAvailable(timeout=1):
        try:
            response = urlopen(Request("/".join([BadIpsIncrBanTime._badips]),
                                       headers={'User-Agent': "Fail2Ban"}),
                               timeout=timeout)
            return True, ''
        except Exception as e:  # pragma: no cover
            return False, e

    def toJson(self, response):
        return json.loads(response.read().decode('utf-8'))

    def ban(self, aInfo):
        try:
            url = "/".join([self._badips, "get", "info", str(aInfo['ip'])])
            self._logSys.debug("Request: %s", url)
            response = urlopen(self._Request(url), timeout=self.timeout)
        except HTTPError as response:
            messages = self.toJson(response)
            self._logSys.error(
                "Response from badips.com: '%s'",
                messages['err'])
            raise
        else:
            messages = self.toJson(response)
            self._logSys.debug("Response from badips.com '%s'", messages['suc'])
            if messages['Listed'] == True:
                banTime = self._jail.actions.getBanTime() + self.time_increment
                self._logSys.debug("Increase ban time for %s to %i", aInfo['ip'], banTime)
                self._jail.actions.setBanTime(banTime)

    def start(self):
        self._logSys.debug("BadIpsIncrBanTime action started for %s", self._jail.name)

Action = BadIpsIncrBanTime

