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

from cuwo.constants import BLOCK_SCALE
from cuwo.script import ConnectionScript
from cuwo.script import ServerScript
from cuwo.vector import Vector2

try:
    from cuwo.world import World
    has_world = True
except ImportError:
    has_world = False
    
try:
    from cuwo.tgen import BlockType
    block_types_available = True
except ImportError:
    block_types_available = False

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
        self.particles = []
        self.chunks = []
        self.__first_pos_update = True

    def on_pos_update(self, event):
        p = self.connection.position
        pos_x = int(p.x / (BLOCK_SCALE * 256))
        pos_y = int(p.y / (BLOCK_SCALE * 256))

        if self.__first_pos_update:
            self.__first_pos_update = False
            self.__chunk_pos = (pos_x, pos_y)
            w = self.server.world
            for x in range(-1, 2):
                for y in range(-1, 2):
                    pos = Vector2(pos_x + x, pos_y + y)
                    self.chunks.append(w.get_chunk(pos))
        else:
            cp = self.__chunk_pos
            if (pos_x,pos_y) != cp:
                # request chunk data
                w = self.server.world
                for x in range(-1, 2):
                    for y in range(-1, 2):
                        cx = pos_x + x
                        cy = pos_y + y
                        if abs(cx - cp[0]) > 1 or abs(cy - cp[1]) > 1:
                            pos = Vector2(cx, cy)
                            chunk = w.get_chunk(pos)
                            if chunk not in self.chunks:
                                self.chunks.append(chunk)
                self.__chunk_pos = (pos_x,pos_y)

    def on_entity_update(self, event):
        """Handles an entity update event.
        
        Keyword arguments:
        event -- Event parameter
        
        """
        self.entity.cubolt_entity.on_entity_update(event)

    def send_update_packet(self, update_packet):
        """Creates and sends an individual update packet for this
        client.
        
        Keyword arguments:
        update_packet -- Update packet to send.

        """
        block_deltas = []
        not_loaded_chunks = []
        for chunk in self.chunks:
            if chunk.data is None:
                not_loaded_chunks.append(chunk)
            else:
                chunk._append_deltas(block_deltas)
        self.chunks = not_loaded_chunks

        # backup non player specific data
        block_deltas_backup = update_packet.items_1
        particle_backup = update_packet.particles
        
        # generate new data
        update_packet.items_1 = block_deltas_backup + block_deltas
        update_packet.particles = particle_backup + self.particles

        # send updated packet
        self.connection.send_packet(update_packet)

        # restore backupped data
        update_packet.items_1 = block_deltas_backup
        update_packet.particles = particle_backup

        self.particles.clear()

    def is_near(self, x, y):
        """Checks whether a client is near a given chunk.
        
        Keyword arguments:
        x -- Chunk x coordinate.
        y -- Chunk y coordinate.

        Returns:
        True, if the player is near the chunk, otherwise False.

        """
        c = self.connection
        if c is not None:
            chunk = c.chunk
            if chunk is not None:
                c_pos = chunk.pos
                if abs(x - c_pos.x) < 1 and abs(y - c_pos.y) < 1:
                    return True
        return False
        
        
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
        if not block_types_available:
            print(('[CB] Can not inject terrain module modification' +
                   ', this may break some scripts. To use the ' +
                   'terrain module modifications a cuwo build ' +
                   'newer than f8b2c4da58 is needed.'))
        self.injector.inject_world_modification()
        
        needed = time.time() - begin
        print('[CB] Done (%.2fs).' % needed)
        
        
def get_class():
    """Gets the ServerScript instance to register.
    
    Return value:
    ServerScript to register, in this case it's the
    CuBoltServerScript.
    
    """
    return CuBoltServerScript