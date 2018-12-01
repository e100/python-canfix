#!/usr/bin/env python

#  CAN-FIX Protocol Module - An Open Source Module that abstracts communication
#  with the CAN-FIX Aviation Protocol
#  Copyright (c) 2012 Phil Birkelbach
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import can
from ..globals import *

class NodeSpecific(object):
    """Represents a generic Node Specific Message"""
    codes = ["Node Identification", "Bit Rate Set", "Node ID Set", "Disable Parameter",
             "Enable Parameter", "Node Report", "Node Status", "Update Firmware",
             "Connection Request", "Node Configuration Set", "Node Configuration Query",
             "Node Description", "Parameter Set 0", "Parameter Set 32", "Parameter Set 64",
             "Parameter Set 96", "Parameter Set 128", "Parameter Set 160", "Parameter Set 192",
             "Parameter Set 224"]

    def __init__(self, msg=None):
        if msg != None:
            self.setMessage(msg)
        else:
            self.controlCode = 0
            self.data = bytearray([])

    def setMessage(self, msg):
        log.debug(str(msg))
        self.sendNode = msg.arbitration_id -1792
        self.controlCode = msg.data[0]
        #self.destNode = msg.data[1]
        self.data = msg.data[1:]

    def getMessage(self):
        msg = can.Message(arbitration_id=self.sendNode + 1792, extended_id=False)
        msg.data.append(self.controlCode)
        #msg.data.append(self.destNode)
        for each in self.data:
            msg.data.append(each)
        msg.dlc = len(msg.data)
        return msg

    msg = property(getMessage, setMessage)

    def getParameterID(self):
        """This is a convenience function that assembles and returns
            the parameter id for Disable/Enable Parameter messages"""
        return (data[1] << 8) + data[0]

    def __str__(self):
        s = "[{}] ".format(str(self.sendNode))
        try:
            s += self.codes[self.controlCode]
        except IndexError:
            if self.controlCode < 128:
                s += "Reserved NSM "
            else:
                s += "User Defined NSM "
            s += str(self.controlCode)
        for each in self.data:
            s += " 0x{:02x}".format(each)
            #s += hex(each)
        return s


class NodeIdentification(NodeSpecific):
    def __init__(self, msg=None, device=None, fwrev=None, model=None):
        if msg != None:
            self.setMessage(msg)
        else:
            self.controlCode = 0x00
            self.msgType = MSG_REQUEST
            self.sendNode = None
            self.destNode = None
            if device is not None: self.device = device
            if fwrev is not None: self.fwrev = fwrev
            if model is not None: self.model = model

    def setMessage(self, msg):
        log.debug(str(msg))
        self.sendNode = msg.arbitration_id -1792
        self.controlCode = msg.data[0]
        assert self.controlCode == 0x00
        self.destNode = msg.data[1]
        if msg.dlc == 2:
            self.msgType = MSG_REQUEST
        elif msg.dlc == 8:
            self.msgType = MSG_RESPONSE
            self.device = msg.data[3]
            self.fwrev = msg.data[4]
            self.model = msg.data[5] + (msg.data[6]<<8) + (msg.data[7]<<16)
        else:
            raise MsgSizeError("Message size is incorrect")

    def getMessage(self):
        msg = can.Message(arbitration_id=self.sendNode + 1792, extended_id=False)
        msg.data = self.data
        msg.dlc = len(msg.data)
        return msg

    msg = property(getMessage, setMessage)

    def getData(self):
        data = bytearray([])
        data.append(self.controlCode)
        data.append(self.destNode)
        if self.msgType == MSG_RESPONSE:
            data.append(0x01) # CAN-FIX Specification Revision
            data.append(self.device)
            data.append(self.fwrev)
            data.extend([self.model & 0x0000FF, (self.model & 0x00FF00) >> 8, (self.model & 0xFF0000) >> 16])

        return data

    data = property(getData)

    def setDevice(self, device):
        if device > 255 or device < 0:
            raise ValueError("Device ID must be between 0 and 255")
        else:
            self.__device = device
            self.msgType = MSG_RESPONSE

    def getDevice(self):
        return self.__device

    device = property(getDevice, setDevice)

    def setFwrev(self, fwrev):
        if fwrev > 255 or fwrev < 0:
            raise ValueError("Firmware Revision must be between 0 and 255")
        else:
            self.__fwrev = fwrev
            self.msgType = MSG_RESPONSE


    def getFwrev(self):
        return self.__fwrev

    fwrev = property(getFwrev, setFwrev)

    def setModel(self, model):
        if model < 0 or model > 0xFFFFFF:
            raise ValueError("Model must be between 0 and 0xFFFFFF")
        else:
            self.__model = model
            self.msgType = MSG_RESPONSE

    def getModel(self):
        return self.__model

    model = property(getModel, setModel)

    def __str__(self):
        s = "[" + str(self.sendNode) + "]"
        s += "->[" + str(self.destNode) + "] "
        s += self.codes[self.controlCode]
        s += ": device={}".format(self.device)
        s += ", fwrev={}".format(self.fwrev)
        s += ", model={}".format(self.model)
        return s


class BitRateSet(NodeSpecific):
    def __init__(self, msg=None, bitrate=None):
        if msg != None:
            self.setMessage(msg)
        else:
            self.controlCode = 0x01
            self.msgType = MSG_RESPONSE
            self.status = MSG_SUCCESS
            self.sendNode = None
            self.destNode = None
            if bitrate is not None: self.bitrate = bitrate

    def setMessage(self, msg):
        log.debug(str(msg))
        self.sendNode = msg.arbitration_id -1792
        self.controlCode = msg.data[0]
        assert self.controlCode == 0x01
        self.destNode = msg.data[1]

        if msg.dlc == 2:
            self.msgType = MSG_RESPONSE
            self.status = MSG_SUCCESS
        elif msg.dlc == 3:
            if msg.data[2] == 0xFF:
                self.msgType = MSG_RESPONSE
                self.status = MSG_FAIL
            else:
                self.msgType = MSG_REQUEST
                self.bitrate = msg.data[2]
        else:
            raise MsgSizeError("Message size is incorrect")

    def getMessage(self):
        msg = can.Message(arbitration_id=self.sendNode + 1792, extended_id=False)
        msg.data = self.data
        msg.dlc = len(msg.data)
        return msg

    msg = property(getMessage, setMessage)

    def getData(self):
        data = bytearray([])
        data.append(self.controlCode)
        data.append(self.destNode)
        if self.msgType == MSG_RESPONSE and self.status == MSG_FAIL:
            data.append(0xFF)
        elif self.msgType == MSG_REQUEST:
            data.append(self.bitrate)
        return data

    data = property(getData)

    bitrates = {125:1, 250:2, 500:3, 1000:4}

    def setBitRate(self, bitrate):
        if bitrate >= 1 and bitrate <= 4:
            self.__bitrate = bitrate
        elif bitrate in self.bitrates:
            self.__bitrate = self.bitrates[bitrate]
        else:
            raise ValueError("Invalid Bit Rate Given")
        self.msgType = MSG_REQUEST

    def getBitRate(self):
        return self.__bitrate

    bitrate = property(getBitRate, setBitRate)

    def __str__(self):
        s = "[" + str(self.sendNode) + "]"
        s += "->[" + str(self.destNode) + "] "
        s += self.codes[self.controlCode]
        if self.msgType == MSG_REQUEST:
            for each in self.bitrates:
                if self.bitrates[each] == self.bitrate:
                    b = each
                    break
            s += ": request bitrate={}kbps".format(b)
        else:
            if self.status == MSG_SUCCESS:
                s += ": Success Response"
            elif self.status == MSG_FAIL:
                s += ": Failure Response"
        return s


class NodeIDSet(NodeSpecific):
    def __init__(self, msg=None, newnode=None):
        if msg != None:
            self.setMessage(msg)
        else:
            self.controlCode = 0x02
            self.msgType = MSG_RESPONSE
            self.sendNode = None
            self.destNode = None
            if newnode is not None: self.newnode = newnode

    def setMessage(self, msg):
        log.debug(str(msg))
        self.sendNode = msg.arbitration_id -1792
        self.controlCode = msg.data[0]
        assert self.controlCode == 0x02
        self.destNode = msg.data[1]

        if msg.dlc == 3:
            if msg.data[2] == 0x00:
                self.msgType = MSG_RESPONSE
            else:
                self.msgType = MSG_REQUEST
                self.newnode = msg.data[2]
        else:
            raise MsgSizeError("Message size is incorrect")

    def getMessage(self):
        msg = can.Message(arbitration_id=self.sendNode + 1792, extended_id=False)
        msg.data = self.data
        msg.dlc = len(msg.data)
        return msg

    msg = property(getMessage, setMessage)

    def getData(self):
        data = bytearray([])
        data.append(self.controlCode)
        data.append(self.destNode)
        if self.msgType == MSG_RESPONSE:
            data.append(0x00)
        elif self.msgType == MSG_REQUEST:
            data.append(self.newnode)
        return data

    data = property(getData)

    def setNewNode(self, newnode):
        if newnode >= 1 and newnode <= 255:
            self.__newnode = newnode
        else:
            raise ValueError("Invalid Node Number Given")
        self.msgType = MSG_REQUEST

    def getNewNode(self):
        return self.__newnode

    newnode = property(getNewNode, setNewNode)

    def __str__(self):
        s = "[" + str(self.sendNode) + "]"
        s += "->[" + str(self.destNode) + "] "
        s += self.codes[self.controlCode]
        if self.msgType == MSG_REQUEST:
            s += ": request new node id={}".format(self.newnode)
        else:
            s += ": Success Response"
        return s
