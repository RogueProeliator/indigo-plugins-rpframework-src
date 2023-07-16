#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkNetworkingUPnP by RogueProeliator <adam.d.ashe@gmail.com>
# Classes that handle various aspects of Universal Plug and Play protocols such as
# discovery of devices.
#######################################################################################

# region Python Imports
from __future__ import absolute_import
import socket

import http.client as httplib
from io import StringIO

from .RPFrameworkUtils import to_unicode


# endregion


class SSDPResponse(object):
    def __init__(self, response):
        self.location = ""
        self.usn = ""
        self.st = ""
        self.server = ""
        self.cache = ""

        parsed_headers = {}
        lines = response.split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                parsed_headers[key.lower().strip()] = value.strip()

        if parsed_headers.get("location", None) is not None:
            self.location = parsed_headers["location"]

        if parsed_headers.get("usn", None) is not None:
            self.usn = parsed_headers["usn"]

        if parsed_headers.get("st", None) is not None:
            self.st = parsed_headers["st"]

        if parsed_headers.get("server", None) is not None:
            self.server = parsed_headers["server"]

        if parsed_headers.get("cache-control", None) is not None:
            try:
                cache_control_header = parsed_headers["cache-control"]
                cache_control_header = cache_control_header.split("=")[1]
                self.cache = cache_control_header
            except:
                pass

        self.all_headers = parsed_headers

    def __repr__(self):
        return '<SSDPResponse(%(location)s, %(st)s, %(usn)s, %(server)s)>' % self.__dict__ + f"{self.all_headers}" + '</SSDPResonse>'


def uPnPDiscover(service, timeout=3, retries=1, logger=None):
    group = ("239.255.255.250", 1900)
    message = "\r\n".join([
        "M-SEARCH * HTTP/1.1",
        f"HOST: {group[0]}:{group[1]}",
        "MAN: ""ssdp:discover""",
        "ST: " + service, "MX: 3", "", ""])
    socket.setdefaulttimeout(timeout)
    responses = []
    for _ in range(retries):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.sendto(message.encode(), group)
        while True:
            try:
                decoded_string = sock.recv(1024).decode()
                logger.threaddebug(decoded_string)
                response = SSDPResponse(decoded_string)
                responses.append(response)
            except socket.timeout:
                break
    return responses
