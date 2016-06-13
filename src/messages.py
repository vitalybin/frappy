#  -*- coding: utf-8 -*-
# *****************************************************************************
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Enrico Faulhaber <enrico.faulhaber@frm2.tum.de>
#
# *****************************************************************************

"""Define SECoP Messages"""

from lib import attrdict
import time
from device import get_device_pars, get_device_cmds

class Request(object):
    """Base class for all Requests"""
    pars = []
    def __repr__(self):
        pars = ', '.join('%s=%r' % (k, self.__dict__[k]) for k in self.pars)
        s = '%s(%s)' % (self.__class__.__name__, pars)
        return s

class Reply(object):
    """Base class for all Replies"""
    pars = []
    def __repr__(self):
        pars = ', '.join('%s=%r' % (k, self.__dict__[k]) for k in self.pars)
        s = '%s(%s)' % (self.__class__.__name__, pars)
        return s


class ListDevicesRequest(Request):
    pass

class ListDevicesReply(Reply):
    pars = ['list_of_devices']
    def __init__(self, args):
        self.list_of_devices = args


class ListDeviceParamsRequest(Request):
    pars = ['device']
    def __init__(self, device):
        self.device = device

class ListDeviceParamsReply(Reply):
    pars = ['device', 'params']
    def __init__(self, device, params):
        self.device = device
        self.params = params

class ReadValueRequest(Request):
    pars = ['device', 'maxage']
    def __init__(self, device, maxage=0):
        self.device = device
        self.maxage = maxage

class ReadValueReply(Reply):
    pars = ['device', 'value', 'timestamp', 'error', 'unit']
    def __init__(self, device, value, timestamp=0, error=0, unit=None):
        self.device = device
        self.value = value
        self.timestamp = timestamp
        self.error = error
        self.unit = unit


class ReadParamRequest(Request):
    pars = ['device', 'param', 'maxage']
    def __init__(self, device, param, maxage=0):
        self.device = device
        self.param = param
        self.maxage = maxage

class ReadParamReply(Reply):
    pars = ['device', 'param', 'value', 'timestamp', 'error', 'unit']
    def __init__(self, device, param, value, timestamp=0, error=0, unit=None):
        self.device = device
        self.param = param
        self.value = value
        self.timestamp = timestamp
        self.error = error
        self.unit = unit


class WriteParamRequest(Request):
    pars = ['device', 'param', 'value']
    def __init__(self, device, param, value):
        self.device = device
        self.param = param
        self.value = value

class WriteParamReply(Reply):
    pars = ['device', 'param', 'readback_value', 'timestamp', 'error', 'unit']
    def __init__(self, device, param, readback_value, timestamp=0, error=0,
                 unit=None):
        self.device = device
        self.param = param
        self.readback_value = readback_value
        self.timestamp = timestamp
        self.error = error
        self.unit = unit


class RequestAsyncDataRequest(Request):
    pars = ['device', 'params']
    def __init__(self, device, *args):
        self.device = device
        self.params = args

class RequestAsyncDataReply(Reply):
    pars = ['device', 'paramvalue_list']
    def __init__(self, device, *args):
        self.device = device
        self.paramvalue_list = args

class AsyncDataUnit(ReadParamReply):
    pass


class ListOfFeaturesRequest(Request):
    pass

class ListOfFeaturesReply(Reply):
    pars = ['features']
    def __init__(self, *args):
        self.features = args

class ActivateFeatureRequest(Request):
    pars = ['feature']
    def __init__(self, feature):
        self.feature = feature

class ActivateFeatureReply(Reply):
    # Ack style or Error
    # may be should reply with active features?
    pass


FEATURES = [
    'Feature1',
    'Feature2',
    'Feature3',
]


# Error replies:

class ErrorReply(Reply):
    pars = ['error']
    def __init__(self, error):
        self.error = error

class NoSuchDeviceErrorReply(ErrorReply):
    pars = ['device']
    def __init__(self, device):
        self.device = device

class NoSuchParamErrorReply(ErrorReply):
    pars = ['device', 'param']
    def __init__(self, device, param):
        self.device = device
        self.param = param

class ParamReadonlyErrorReply(ErrorReply):
    pars = ['device', 'param']
    def __init__(self, device, param):
        self.device = device
        self.param = param

class UnsupportedFeatureErrorReply(ErrorReply):
    pars = ['feature']
    def __init__(self, feature):
        self.feature = feature

class NoSuchCommandErrorReply(ErrorReply):
    pars = ['device', 'command']
    def __init__(self, device, command):
        self.device = device
        self.command = command

class CommandFailedErrorReply(ErrorReply):
    pars = ['device', 'command']
    def __init__(self, device, command):
        self.device = device
        self.command = command

class InvalidParamValueErrorReply(ErrorReply):
    pars = ['device', 'param', 'value']
    def __init__(self, device, param, value):
        self.device = device
        self.param = param
        self.value = value

class MessageHandler(object):
    """puts meaning to the request objects"""
    def handle_ListDevices(self, msgargs):
        return ListDevicesReply(self.listDevices())

    def handle_ListDeviceParams(self, msgargs):
        devobj = self.getDevice(msgargs.device)
        if devobj:
            return ListDeviceParamsReply(msgargs.device,
                                         get_device_pars(devobj))
        else:
            return NoSuchDeviceErrorReply(msgargs.device)

    def handle_ReadValue(self, msgargs):
        devobj = self.getDevice(msgargs.device)
        if devobj:
            return ReadValueReply(msgargs.device, devobj.read_value(),
                                  timestamp=time.time())
        else:
            return NoSuchDeviceErrorReply(msgargs.device)

    def handle_ReadParam(self, msgargs):
        devobj = self.getDevice(msgargs.device)
        if devobj:
            readfunc = getattr(devobj, 'read_%s' % msgargs.param, None)
            if readfunc:
                return ReadParamReply(msgargs.device, msgargs.param,
                                      readfunc(), timestamp=time.time())
            else:
                return NoSuchParamErrorReply(msgargs.device, msgargs.param)
        else:
            return NoSuchDeviceErrorReply(msgargs.device)

    def handle_WriteParam(self, msgargs):
        devobj = self.getDevice(msgargs.device)
        if devobj:
            writefunc = getattr(devobj, 'write_%s' % msgargs.param, None)
            if writefunc:
                readbackvalue = writefunc(msgargs.value) or msgargs.value
                return WriteParamReply(msgargs.device, msgargs.param,
                                       readbackvalue,
                                       timestamp=time.time())
            else:
                if getattr(devobj, 'read_%s' % msgargs.param, None):
                    return ParamReadonlyErrorReply(msgargs.device,
                                                   msgargs.param)
                else:
                    return NoSuchParamErrorReply(msgargs.device,
                                                 msgargs.param)
        else:
            return NoSuchDeviceErrorReply(msgargs.device)

    def handle_RequestAsyncData(self, msgargs):
        return ErrorReply('AsyncData is not (yet) supported')

    def handle_ListOfFeatures(self, msgargs):
        # no features supported (yet)
        return ListOfFeaturesReply([])

    def handle_ActivateFeature(self, msgargs):
        return ErrorReply('Features are not (yet) supported')

    def unhandled(self, msgname, msgargs):
        """handler for unhandled Messages

        (no handle_<messagename> method was defined)
        """
        self.log.error('IGN: got unhandled request %s' % msgname)
        return ErrorReply('Got Unhandled Request')


def parse(message):
    # parses a message and returns
    # msgtype, msgname and parameters of message (as dict)
    msgtype = 'unknown'
    msgname = 'unknown'
    if isinstance(message, ErrorReply):
        msgtype = 'error'
        msgname = message.__class__.__name__[:-len('Reply')]
    elif isinstance(message, Request):
        msgtype = 'request'
        msgname = message.__class__.__name__[:-len('Request')]
    elif isinstance(message, Reply):
        msgtype = 'reply'
        msgname = message.__class__.__name__[:-len('Reply')]
    return msgtype, msgname, \
           attrdict([(k, getattr(message, k)) for k in message.pars])

__ALL__ = ['ErrorReply',
           'NoSuchDeviceErrorReply', 'NoSuchParamErrorReply'
           'ParamReadonlyErrorReply', 'UnsupportedFeatureErrorReply',
           'NoSuchCommandErrorReply', 'CommandFailedErrorReply',
           'InvalidParamValueErrorReply',
           'Reply',
           'ListDevicesReply', 'ListDeviceParamsReply', 'ReadValueReply',
           'ReadParamReply', 'WriteParamReply', 'RequestAsyncDataReply',
           'AsyncDataUnit', 'ListOfFeaturesReply', 'ActivateFeatureReply',
           'Request',
           'ListDevicesRequest', 'ListDeviceParamsRequest', 'ReadValueRequest',
           'ReadParamRequest', 'WriteParamRequest', 'RequestAsyncDataRequest',
           'ListOfFeaturesRequest', 'ActivateFeatureRequest',
           'parse', 'MessageHandler',
]

if __name__ == '__main__':
    print "minimal testing: transport"
    testcases = dict(
        error=[ErrorReply(),
               NoSuchDeviceErrorReply('device3'),
               NoSuchParamErrorReply('device2', 'param3'),
               ParamReadonlyErrorReply('device1', 'param1'),
               UnsupportedFeatureErrorReply('feature5'),
               NoSuchCommandErrorReply('device1', 'fance_command'),
               CommandFailedErrorReply('device1', 'stop'),
               InvalidParamValueErrorReply('device1', 'param2', 'STRING_Value'),
              ],
        reply=[Reply(),
               ListDevicesReply('device1', 'device2'),
               ListDeviceParamsReply('device', ['param1', 'param2']),
               ReadValueReply('device2', 3.1415),
               ReadParamReply('device1', 'param2', 2.718),
               WriteParamReply('device1', 'param2', 2.718),
               RequestAsyncDataReply('device1', '?what to put here?'),
               AsyncDataUnit('device1', 'param2', 2.718),
               ListOfFeaturesReply('feature1', 'feature2'),
               ActivateFeatureReply(),
              ],
        request=[Request(),
                 ListDevicesRequest(),
                 ListDeviceParamsRequest('device1'),
                 ReadValueRequest('device2'),
                 ReadParamRequest('device1', 'param2'),
                 WriteParamRequest('device1', 'param2', 2.718),
                 RequestAsyncDataRequest('device1', ['param1', 'param2']),
                 ListOfFeaturesRequest(),
                 ActivateFeatureRequest('feature1'),
                ],
    )
    for msgtype, msgs in testcases.items():
        print "___ testing %ss ___" % msgtype
        for msg in msgs:
            print msg.__class__.__name__, 'is', msgtype,
            decoded = parse(msg)
            if decoded[0] != msgtype:
                print "\tFAIL, got %r but expected %r" %(decoded[0], msgtype)
            else:
                print "\tOk"
        print

