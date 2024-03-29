#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# RPFrameworkNetworkingWOL by RogueProeliator <adam.d.ashe@gmail.com>
# 	Classes that handles send Wake-On-LAN (WOL) requests over the network
#######################################################################################

#region Python imports
import socket
import struct
#endregion


def sendWakeOnLAN(macaddress):
    # Check macaddress format and try to compensate.
    if len(macaddress) == 12:
        pass
    elif len(macaddress) == 12 + 5:
        sep = macaddress[2]
        macaddress = macaddress.replace(sep, "")
    else:
        raise ValueError("Incorrect MAC address format")
 
    # Pad the synchronization stream.
    data = ''.join(["FFFFFFFFFFFF", macaddress * 20])
    send_data = '' 

    # Split up the hex values and pack.
    for i in range(0, len(data), 2):
        send_data = ''.join([send_data, struct.pack("B", int(data[i: i + 2], 16))])

    # Broadcast it to the LAN.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(send_data, ("<broadcast>", 7))
