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
import sys

from cuwo.constants import FULL_MASK
from cuwo.packet import ChunkItems
from cuwo.packet import Packet4Struct1 as BlockDeltaUpdate
from cuwo.types import AttributeDict
from cuwo.vector import Vector2
from cuwo.vector import Vector3

try:
    from cuwo.tgen import BlockType
    block_types_available = True
except ImportError:
    block_types_available = False


class CuBoltChunk:
    data = None

    def __init__(self, world, pos):
        self.world = world
        self.pos = pos
        self.items = []
        self.static_entities = {}
        self.block_cache = []

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
                cb = entity.cubolt_entity
                cb.on_entity_update(AttributeDict(mask=FULL_MASK))
                # inserted end
                
                entity.reset()

        # inserted
        # if the server already supports block types we can use copy on write
        # to make terrain editations much easier
        if block_types_available:
            self.data = CuBoltTGenChunk(self.world.server, self.data)
        # inserted end

        self.update()
        
        # inserted
        # do the cached calls that have been made before the chunk
        # was loaded
        for (pos, bt) in self.block_cache:
            self.set_block(pos, bt)
        self.block_cache = None

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

    def update(self):
        self.world.server.updated_chunks.add(self)

    def on_update(self, update_packet):
        item_list = ChunkItems()
        item_list.chunk_x, item_list.chunk_y = self.pos
        item_list.items = self.items
        update_packet.chunk_items.append(item_list)

    def on_post_update(self):
        for item in self.items:
            item.drop_time = 0

    def get_block(self, position):
        """Gets a block from this chunk.
        
        Keyword arguments:
        position -- Position vector. X, Y, Z coordinate from 0-255.

        Returns:
        Tuple of form (color tuple, block type) or None if the chunk
        has not yet been generated.

        """
        if self.data is None:
            return None
        if block_types_available:
            return self.data.get_block(position)
        else:
            return None

    def set_block(self, position, block_tuple):
        """Sets a block in this chunk.
        
        Keyword arguments:
        position -- Position vector. X, Y, Z coordinate form 0-255.
        block_tuple -- Tuple of form (color tuple, block type).

        """
        if self.data is None: # Need to cache calls and do them later
            self.block_cache.append((position, block_tuple))
        else:
            if block_types_available:
                self.data.set_block(position, block_tuple)

    def _append_deltas(self, deltas):
        """Appends the deltas for this chunk. Access to data is safe
        here.
        
        Keyword arguments:
        deltas -- List to append to.

        """
        self.data._append_deltas(deltas)


class CuBoltTGenChunk:
    def __init__(self, server, tgen_chunk):
        self.__server = server
        self.__tgen_chunk = tgen_chunk
        self.items = tgen_chunk.items
        self.static_entities = tgen_chunk.static_entities
        self.dynamic_entities = tgen_chunk.dynamic_entities
        self.x = tgen_chunk.x
        self.y = tgen_chunk.y

        self.__proxies = {}

        self.get_render = tgen_chunk.get_render

    def get_solid(self, x, y, z):
        if x < 0 or x >= 256 or y < 0 or y >= 256: 
            return False 
        data = self[x + y * 256] 
        if z < data.a: 
            return True 
        z -= data.a 
        if z >= len(data): 
            return False 
        return data.get_type(z) != EMPTY_TYPE

    def get_neighbor_solid(self, x, y, z): 
        return (self.get_solid(x - 1, y, z) and 
                self.get_solid(x + 1, y, z) and 
                self.get_solid(x, y + 1, z) and 
                self.get_solid(x, y - 1, z) and 
                self.get_solid(x, y, z + 1) and 
                self.get_solid(x, y, z - 1)) 

    def get_dict(self): 
        blocks = {} 
 
        for i in range(256*256): 
            x = i % 256 
            y = i / 256 
            xy = self[x + y * 256] 
            for z in range(xy.b, (xy.a + len(xy))): 
                if self.get_neighbor_solid(x, y, z): 
                    continue
                if z < xy.a: 
                    blocks[(x, y, z)] = xy[0] 
                    continue
                if xy.get_type(z - xy.a) == EMPTY_TYPE: 
                    continue
                blocks[(x, y, z)] = xy[z - xy.a]
        return blocks

    def get_height(self, x, y):
        data = self[x + y * 256]
        return data.height

    def __getitem__(self, index):
        if index in self.__proxies:
            return self.__proxies[index]
        else:
            native_proxy = self.__tgen_chunk[index]
            server = self.__server
            x = index % 256
            y = index / 256
            cb_proxy = CuBoltXYProxy(server, self, native_proxy, x, y)
            self.__proxies[index] = cb_proxy
            return cb_proxy

    def get_column(self, x, y):
        """Gets a "column" of blocks of this chunk by coordinates.
        
        Keyword arguments:
        x -- X chunk coordinate (0-255).
        y -- Y chunk coordinate (0-255).

        """
        return self[x + y * 256]
    
    def get_block(self, position):
        """Gets a block from this chunk.
        
        Keyword arguments:
        position -- Position vector. X, Y, Z coordinate from 0-255.

        Returns:
        Tuple of form (color tuple, block type).

        """
        p = position
        x = int(p.x)
        y = int(p.y)
        z = int(p.z)
        proxy = self.get_column(x, y)
        return proxy.get_block(z)

    def set_block(self, position, block_tuple):
        """Sets a block in this chunk.
        
        Keyword arguments:
        position -- Position vector. X, Y, Z coordinate form 0-255.
        block_tuple -- Tuple of form (color tuple, block type).

        """
        p = position
        x = int(p.x)
        y = int(p.y)
        z = int(p.z)
        proxy = self.get_column(x, y)
        proxy.set_block(z, block_tuple)

    def _append_deltas(self, deltas):
        """Appends the deltas for this chunk.
        
        Keyword arguments:
        deltas -- List to append to.

        """
        for proxy in self.__proxies.values():
            proxy._append_deltas(deltas)


class CuBoltXYProxy:
    def __init__(self, server, chunk, proxy, x, y):
        self.__server = server
        self.__proxy = proxy
        self.__x = x + chunk.x * 256
        self.__y = y + chunk.y * 256
        self.__chunk_x = chunk.x
        self.__chunk_y = chunk.y
        self.__blocks = {}
        self.height = proxy.a + len(proxy)

    @property
    def a(self):
        return self.__proxy.a

    @property
    def b(self):
        return self.__proxy.b

    def __len__(self):
        return len(self.__proxy)

    def __getitem__(self, index):
        abs_index = index + self.__proxy.a
        if abs_index in self.__blocks:
            return self.__blocks[abs_index][0]
        elif index > 0 and index < len(self.__proxy):
            return self.__proxy[index]
        elif index < 0:
            return self[0]
        else:
            return (0,0,0) # Empty block

    def get_type(self, index):
        abs_index = index + self.__proxy.a
        if abs_index in self.__blocks:
            return self.__blocks[abs_index][1]
        elif index > 0 and index < len(self.__proxy):
            return self.__proxy.get_type(index)
        elif index < 0:
            return MOUNTAIN_TYPE
        else:
            return EMPTY_TYPE

    def get_block(self, index):
        """Absolute block access.
        
        Keyword arguments:
        index -- Absolute index to access at. Index recalculation is
        done internally.

        Returns:
        A tuple of (block color as 3 tuple, block type).
        
        """
        if index in self.__blocks:
            return self.__blocks[index]
        else:
            rel_index = index - self.__proxy.a
            n_color = self.__proxy[rel_index]
            n_type = self.__proxy.get_type(rel_index)
            return (n_color,n_type)

    def set_block(self, index, block_tuple):
        """Absolute block set.
        
        Keyword arguments:
        index -- Absolute index to write to.
        block_tuple -- Tuple of form (block color as 3 tuple,
            block type).

        """
        rel_index = index - self.__proxy.a
        n_color = self.__proxy[rel_index]
        n_type = self.__proxy.get_type(rel_index)
        changed = False
        if block_tuple[0] == n_color and block_tuple[1] == n_type:
            if index in self.__blocks:
                del self.__blocks[index]
                changed = True
                if index == self.height:
                    # Search the first non-air block
                    self.height = self.height - 1
                    while self.get_block(self.height)[1] == EMPTY_TYPE:
                        self.height = self.height - 1
        else:
            self.__blocks[index] = block_tuple
            changed = True
            if index >= self.height:
                self.height = index + 1
        
        if changed:
            cubolt = self.__server.scripts.cubolt
            x = self.__chunk_x
            y = self.__chunk_y
            w = self.__server.world
            for connection_script in cubolt.children:
                if connection_script.is_near(x, y):
                    c = w.get_chunk(Vector2(x, y))
                    connection_script.chunks.append(c)
            
    def _append_deltas(self, deltas):
        """Appends the deltas for this chunk.
        
        Keyword arguments:
        deltas -- List to append to.

        """
        for z in self.__blocks.keys():
            bdu = BlockDeltaUpdate()
            # All coordinates are specified absolute in block
            # coordinates
            bdu.block_pos = Vector3(self.__x, self.__y, z)
            block = self.__blocks[z]
            bdu.color_red = block[0][0]
            bdu.color_green = block[0][1]
            bdu.color_blue = block[0][2]
            bdu.block_type = block[1]
            bdu.something8 = 0
            deltas.append(bdu)