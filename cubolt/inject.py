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


"""Code injected into cuwo."""


import asyncio

from cuwo.loop import LoopingCall
from cuwo.packet import CurrentTime
from cuwo.packet import UpdateFinished
from cuwo.tgen import EMPTY_TYPE
from cuwo.vector import Vector2
from cuwo.vector import Vector3

from .entity import EntityExtension
from .model import CubeModel
from .particle import ParticleEffect
from .world import Block
from .world import CuBoltChunk


class Injector(object):
    """Class holding all methods injected into cuwo."""
    def __init__(self, server):
        """Creates the injector.
        
        Keyword arguments:
        server -- Server instance
        
        """
        self.server = server

    def inject_update(self):
        """Injects CuBolts update routine into cuwo."""
        self.update_finished_packet = UpdateFinished()
        self.time_packet = CurrentTime()
        
        self.server.update = self.update
        self.server.update_loop.func = self.server.update
    
    def update(self):
        """CuBolts update routine, replaces cuwos update routine."""
        s = self.server

        s.scripts.call('update')
        
        # entity updates
        # The client doesn't allow friendly display and hostile
        # behaviour, so have a little workaround...
        players = s.players.values()
        for entity in s.world.entities.values():
            entity.cubolt_entity.send(players)
        s.broadcast_packet(self.update_finished_packet)

        # Update particle effects
        for effect in s.particle_effects:
            effect.update()
        
        # other updates
        update_packet = s.update_packet
        for chunk in s.updated_chunks:
            chunk.on_update(update_packet)

        # Send the update packet for this frame. For performance
        # reasons the packets are different for each client
        # (regarding particles and block updates).
        cubolt = s.scripts.cubolt
        for connection in cubolt.children:
            connection.send_update_packet(update_packet)

        update_packet.reset()

        # reset drop times
        for chunk in s.updated_chunks:
            chunk.on_post_update()

        s.updated_chunks.clear()

        # time update
        self.time_packet.time = s.get_time()
        self.time_packet.day = s.get_day()
        s.broadcast_packet(self.time_packet)
        
    def inject_entity(self):
        """Injects entity specific methods."""
        self.server.world.create_entity = self.create_entity
        
    def create_entity(self, entity_id=None):
        """Creates a new entity.
        
        Keyword arguments:
        entity_id -- Static ID for the entity to create
        
        """
        s = self.server
        e = s.world.entity_class(s.world, entity_id)
        self.inject_into_entity(e)
        return e
        
    def inject_into_entity(self, entity):
        """Injects all entity specific methods into the entity.
        
        entity -- cuwo entity to inject into
        
        """
        entity.cubolt_entity = EntityExtension(entity, self.server)
        ce = entity.cubolt_entity
        entity.heal = ce.heal
        entity.stun = ce.stun
        entity.set_relation_to = ce.set_relation_to
        entity.set_relation_to_id = ce.set_relation_to_id
        entity.set_relation_both = ce.set_relation_both
        entity.set_relation_both_id = ce.set_relation_both_id
        entity.teleport = ce.teleport
        entity.destroy = ce.destroy
        entity.is_npc = ce.is_npc
        entity.is_player = ce.is_player
    
    def inject_world_modification(self):
        s = self.server
        w = s.world
        w.server = s
        w.chunk_class = CuBoltChunk
        w.get_block = self.get_block
        w.set_block = self.set_block

    def get_block(self, position):
        """Gets a block.
        
        Keyword arguments:
        position -- Absolute position in block coordinates.

        Returns:
        The block.

        """
        chunk_x = int(position.x) // 256
        chunk_y = int(position.y) // 256
        w = self.server.world
        chunk = w.get_chunk(Vector2(chunk_x, chunk_y))
        x = position.x - chunk_x * 256
        y = position.y - chunk_y * 256
        return chunk.get_block(Vector3(x, y, position.z))

    def set_block(self, position, block):
        """Sets a block.
        
        Keyword arguments:
        position -- Absolute position in block coordinates.
        block -- Block to set.
        
        """
        chunk_x = int(position.x) // 256
        chunk_y = int(position.y) // 256
        w = self.server.world
        chunk = w.get_chunk(Vector2(chunk_x, chunk_y))
        x = position.x - chunk_x * 256
        y = position.y - chunk_y * 256
        chunk.set_block(Vector3(x, y, position.z), block)
        
    def inject_factory(self):
        """Injects CuBolts factory into the server."""
        self.server.cubolt_factory = CuBoltFactory(self.server)
     
        
class CuBoltFactory:
    """A factory for various CuBolt classes."""
    def __init__(self, server):
        """Creates a new CuBoltFactory.
        
        Keyword arguments:
        server -- Current server instance
        
        """
        self.server = server

    def create_particle_effect(self, data=None):
        """Creates a particle effect."""
        return ParticleEffect(self.server, pdata=data)
        
    def load_model(self, filename, from_database=False):
        """Loads a .cub model.
        
        Keyword arguments:
        filename -- Name or path of the file to load
        from_datbase -- True, to load from data1.db, in this case the
            name of the file in the databse must be given, False to 
            load a .cub file, in this case a relative path needs to be
            given
        
        """
        return CubeModel(self.server, filename, from_database)

    def create_block(self, color=(0,0,0), type=EMPTY_TYPE, breakable=False):
        return Block(color, type, breakable)