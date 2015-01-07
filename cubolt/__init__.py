# The MIT License (MIT)
#
# Copyright (c) 2014-2015 Bjoern Lange
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# This file is part of CuBolt.


"""CuBolt module initialization."""


import time


from cuwo.script import ConnectionScript
from cuwo.script import ServerScript


try:
    from cuwo.world import World
    has_world = True
except ImportError:
    has_world = False

from .inject import Injector


class CuBoltConnectionScript(ConnectionScript):
    """Connection script for CuBolt."""
    def __init__(self, parent, connection):
        """Creates a new instance of CuBoltConnectionScript.
        
        Keyword arguments:
        parent -- Parent script
        connection -- Player connection
        
        """
        ConnectionScript.__init__(self, parent, connection)
    
    def on_entity_update(self, event):
        """Handles an entity update event.
        
        Keyword arguments:
        event -- Event parameter
        
        """
        self.entity.cubolt_entity.on_entity_update(event)
    
    def on_flags_update(self, event):
        """Handles an update of the entity flags.
        
        Keyword arguments:
        event -- Event parameter
        
        """
        self.entity.cubolt_entity.on_flags_update(event)
        
        
class CuBoltServerScript(ServerScript):
    """ServerScript for CuBolt."""
    connection_class = CuBoltConnectionScript
    
    def __init__(self, server):
        """Creates a new instance of CuBoltServerScript.
        
        Keyword arguments:
        server -- Server instance
        
        """
        print('[CB] Initializing CuBolt...')
        begin = time.time()
        
        ServerScript.__init__(self, server)
        
        server.particle_effects = []
        
        self.injector = Injector(server)
        self.injector.inject_update()
        self.injector.inject_factory()
        self.injector.inject_entity()
        
        if not has_world:
            print(('[CB] The world module could not be imported, ' + 
                'are you using an old cuwo version?'))
        self.injector.inject_world_modification()
        self.injector.inject_block_methods()
        
        needed = time.time() - begin
        print('[CB] Done (%.2fs).' % needed)
        
        
def get_class():
    """Gets the ServerScript instance to register.
    
    Return value:
    ServerScript to register, in this case it's the
    CuBoltServerScript.
    
    """
    return CuBoltServerScript