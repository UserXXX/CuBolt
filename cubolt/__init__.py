# The MIT License (MIT)
#
# Copyright (c) 2014 Bjoern Lange
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


"""
CuBolt module initialization.
"""


import time


from cuwo.script import ConnectionScript
from cuwo.script import ServerScript


from entity import Entity
from entity import EntityManager


from inject import Injector


class CWConnectionScript(ConnectionScript):
    def __init__(self, parent, connection):
        ConnectionScript.__init__(self, parent, connection)
        self.entity = Entity()
        
    def on_unload(self):
        self.entity.on_unload()
        del self.server.entity_list[self.entity.id]
        
    def on_join(self, event):
        con = self.connection
        em = self.server.entity_manager
        self.entity.init(con.entity_id, con.entity_data, em)
        self.server.entity_list[self.entity.id] = self.entity
    
    def on_entity_update(self, event):
        self.entity.on_entity_update(event)
    
    def on_flags_update(self, event):
        self.entity.on_flags_update(event)

class CWServerScript(ServerScript):
    connection_class = CWConnectionScript
    
    def __init__(self, server):
        print('[CB] Initializing CuBolt...')
        begin = time.time()
        
        ServerScript.__init__(self, server)
        
        server.entity_list = {}
        server.entity_manager = EntityManager(server)
        
        self.injector = Injector()
        self.injector.inject_update(server)
        
        needed = time.time() - begin
        print('[CB] Done (%.2fs).' % needed)
        
        
def get_class():
    return CWServerScript