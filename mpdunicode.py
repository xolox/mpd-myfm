# -*- coding: utf-8 -*
#-------------------------------------------------------------------------------
# Copyright 2010 B. Kroon <bart@tarmack.eu>.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#-------------------------------------------------------------------------------
# This module subclasses the python-mpd module of J.A. Treuman to give it
# Support for unicode strings. It will transform all value strings to unicode
# but leaves the dictionary keys alone.
# It also ads support for the idle, noidle and rescan commands, which seem to
# be missing in the original implementation.
#
# Because it is implemented as a proxy class it is fully transparent. With this
# wrapper it is possible to make your application support unicode without much
# hassle. "import mpdunicode as mpd" in existing code should do the trick.
#-------------------------------------------------------------------------------
from mpd import *

ENCODING = 'utf-8'

if hasattr(MPDClient, '_writecommand'):
    print('mpdunicode: Using python-mpd version 2.1 or older.')
    class MPDClient(MPDClient):
        ''' This proxy class wraps round the python-mpd module.
        It converts the return values to unicode and adds support
        for unicode input.
        '''
        def __init__(self):
            super(MPDClient, self).__init__()
            self._commands.update({'rescan': self._getitem
                                  ,'single': self._getnone
                                  ,'consume': self._getnone
                                  ,'idle': self._getlist
                                  ,'noidle': None
                                  })

        def _writecommand(self, command, args=[]):
            args = [unicode(arg).encode(ENCODING) for arg in args]
            super(MPDClient, self)._writecommand(command, args)

        #def _readline(self):
        #    line = super(MPDClient, self)._readline()
        #    if line is not None:
        #        return line.decode(ENCODING)

        def _readitem(self, separator):
            item = super(MPDClient, self)._readitem(separator)
            if item:
                item[1] = item[1].decode(ENCODING)
            return item

else:
    print('mpdunicode: Using python-mpd version 3.0 or later.')
    class MPDClient(MPDClient):
        ''' This proxy class wraps round the python-mpd module.
        It converts the dictionary values in the output to unicode
        objects and adds support for unicode input.
        '''
        def __init__(self):
            super(MPDClient, self).__init__()

        def _write_command(self, command, args=[]):
            args = [unicode(arg).encode(ENCODING) for arg in args]
            super(MPDClient, self)._write_command(command, args)

        #def _read_line(self):
        #    line = super(MPDClient, self)._read_line()
        #    if line is not None:
        #        return line.decode(ENCODING)

        def _read_pair(self, separator):
            item = super(MPDClient, self)._read_pair(separator)
            if item:
                item[1] = item[1].decode(ENCODING)
            return item

