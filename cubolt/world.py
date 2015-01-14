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


"""World handling."""


import sqlite3
import os.path


from cuwo.constants import FULL_MASK
from cuwo.types import AttributeDict
from cuwo.vector import Vector3


from .constants import BLOCK_TYPE_EMPTY
from .constants import BLOCK_TYPE_MOUNTAIN


class CuBoltChunk:
    data = None

    def __init__(self, world, pos):
        self.world = world
        self.pos = pos
        self.items = []
        self.static_entities = {}

        if not world.use_tgen:
            return

        f = world.get_data(pos)
        f.add_done_callback(self.on_chunk)

    def on_chunk(self, f):
        self.data = f.result()

        self.items.extend(self.data.items)
        self.data.items = []

        for entity_id, data in enumerate(self.data.static_entities):
            header = data.header
            new_entity = self.world.static_entity_class(entity_id, header,
                                                        self)
            self.static_entities[entity_id] = new_entity

        if self.world.use_entities:
            for data in self.data.dynamic_entities:
                entity = self.world.create_entity(data.entity_id)
                data.set_entity(entity)
                
                # inserted
                entity.cubolt_entity.on_entity_update(AttributeDict(mask=FULL_MASK))
                # inserted end
                
                entity.reset()

        self.update()
        
        # inserted
        self.world.server.scripts.call('on_chunk_load', chunk=self)
        # inserted end

    def add_item(self, item):
        self.items.append(item)
        self.update()

    def remove_item(self, index):
        ret = self.items.pop(index).item_data
        self.update()
        return ret

    def get_entity(self, entity_id):
        return self.static_entities[entity_id]

    def on_post_update(self):
        for item in self.items:
            item.drop_time = 0

    def update(self):
        pass


class CuBoltTGenChunk:
    def __init__(self, tgenChunk):
        self.items = tgenChunk.items
        self.static_entities = tgenChunk.entities
        self.dynamic_entities = tgenChunk.dynamic_entities
        self.x = tgenChunk.x
        self.y = tgenChunk.y
        
        
class CuBoltChunkData:
    def __init__(self, tgenChunkData):
        pass
        
# unused from here on
        
class ChunkEntryHelper:
    def __init__(self):
        self.r = 0
        self.g = 0
        self.b = 0
        self.a = 0


class CBChunk:
    def __init__(self, server, x, y, chunk):
        self.server = server
        self.x = x
        self.y = y
        self.chunk = chunk
        
    def get_block(self, pos):
        return CBBlock(self.server, self.chunk.data, pos)
        

class CBBlock:
    def __init__(self, server, tgen_chunk, rel_pos):
        self.__ignore_updates = False
        self.server = server

        chunk_data = tgen_chunk.__data
        chunk_xy = chunk_data.items[(chunk_rel_x, chunk_rel_y)]
        
        lower_end = min(0, chunk_xy.b) # b not actually used, will always be 0
        upper_end = chunk_xy.a + chunk_xy.size
        if self.pos.z < lower_end:
            self.__entry = ChunkEntryHelper()
            self.__ignore_updates = True
            self.r = 0
            self.g = 0
            self.b = 0
            self.type = BLOCK_TYPE_MOUNTAIN
        elif self.pos.z > upper_end:
            self.__entry = ChunkEntryHelper()
            self.__ignore_updates = True
            self.r = 0
            self.g = 0
            self.b = 0
            self.type = BLOCK_TYPE_EMPTY
            # place in block list
            chunk_xy.items[pos.z] = self.__entry
            chunk_xy.size = pos.z - chunk_xy.a
        elif self.pos.z < chunk_xy.a:
            self.__entry = chunk_xy.items[0]
        else:
            try:
                self.__entry = chunk_xy.items[self.pos.z - chunk_xy.a]
            except:
                self.__entry = ChunkEntryHelper()
                self.__ignore_updates = True
                self.r = 0
                self.g = 0
                self.b = 0
                self.type = BLOCK_TYPE_EMPTY
                # place in block list
                chunk_xy.items[pos.z] = self.__entry
        
    @property
    def r(self):
        return self.__entry.r
        
    @r.setter
    def r(self, value):
        self.__entry.r = value
        if not self.__ignore_updates:
            self.server.world.block_changed(self)
        
    @property
    def g(self):
        return self.__entry.g
        
    @g.setter
    def g(self, value):
        self.__entry.g = value
        if not self.__ignore_updates:
            self.server.world.block_changed(self)
        
    @property
    def b(self):
        return self.__entry.b
        
    @b.setter
    def b(self, value):
        self.__entry.b = value
        if not self.__ignore_updates:
            self.server.world.block_changed(self)
        
    @property
    def type(self):
        return self.__entry.a & 0x1F
        
    @type.setter
    def type(self, value):
        value = value & 0x1F # make sure to only use the lowest 5 bits
        self.__entry.a = self.__entry.a & 0xE0 # delete lowest 5 bits
        self.__entry.a = self.__entry.a | value # set lowest 5 bits
        if not self.__ignore_updates:
            self.server.world.block_changed(self)