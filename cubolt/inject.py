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


"""Code injected into cuwo."""


import asyncio


from cuwo.loop import LoopingCall


from cuwo.packet import CurrentTime
from cuwo.packet import Packet4Struct1 # Block delta update
from cuwo.packet import UpdateFinished


from cuwo.vector import Vector3


from .entity import EntityExtension
from .model import CubeModel
from .particle import ParticleEffect
from .world import CBBlock
from .world import CBChunk


class Injector(object):
    """Class holding all methods injected into cuwo."""
    def __init__(self, server):
        """Creates the injector.
        
        Keyword arguments:
        server -- Server instance
        
        """
        self.server = server
        self.__changed_blocks = set()

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
            
        # block updates
        for block in self.__changed_blocks:
            struct = Packet4Struct1()
            struct.block_pos = block.pos # absolute pos
            struct.color_red = block.r
            struct.color_green = block.g
            struct.color_blue = block.b
            struct.block_type = block.a
            struct.something8 = 0
            s.update_packet.items_1.append(struct)
        
        self.__changed_blocks = set()
        
        # entity updates
        # The client doesn't allow friendly display and hostile
        # behaviour, so have a little workaround...
        em = s.entity_manager
        for id, entity in s.world.entities.items():
            em._update_hostility(entity)
            entity.mask = 0 
        s.broadcast_packet(self.update_finished_packet)

        # Update particle effects
        for effect in s.particle_effects:
            effect.update()
        
        # other updates
        update_packet = s.update_packet
        for chunk in s.updated_chunks:
            chunk.on_update(update_packet)
        s.broadcast_packet(update_packet)
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
        em = self.server.entity_manager
        entity.cubolt_entity = EntityExtension(entity, em)
        ce = entity.cubolt_entity
        entity.heal = ce.heal
        entity.stun = ce.stun
        entity.set_hostility_to = ce.set_hostility_to
        entity.set_hostility_to_id = ce.set_hostility_to_id
        entity.set_hostility_to_all = ce.set_hostility_to_all
        entity.destroy = ce.destroy
        
    def inject_block_methods(self):
        self.server.block_changed = self.block_changed
        self.server.get_block = self.get_block
        self.server.get_cb_chunk = self.get_chunk
        
    def block_changed(self, block):
        self.__changed_blocks.append(block)
        
    def get_block(self, x, y, z):
        chunk = self.server.get_chunk(x / 256, y / 256)
        if hasattr(chunk, 'data'):
            return CBBlock(self.server, chunk.data,
                Vector3(x % 256, y % 256, z))
        else:
            return None
        
    def get_chunk(self, x, y):
        chunk = self.server.get_chunk(x, y)
        if hasattr(chunk, 'data'):
            return CBChunk(self.server, x, y,
                chunk.data)
        else:
            return None
        
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