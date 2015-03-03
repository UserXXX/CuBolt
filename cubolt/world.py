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
    from cuwo.tgen import EMPTY_TYPE
    from cuwo.tgen import WATER_TYPE
    from cuwo.tgen import MOUNTAIN_TYPE
    block_types_available = True
except ImportError:
    block_types_available = False

from .exceptions import IndexBelowWorldException

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
        for (pos, block) in self.block_cache:
            self.set_block(pos, block)
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
        The block.

        """
        if self.data is None:
            return None
        if block_types_available:
            return self.data.get_block(position)
        else:
            return None

    def set_block(self, position, block):
        """Sets a block in this chunk.
        
        Keyword arguments:
        position -- Position vector. X, Y, Z coordinate form 0-255.
        block -- The block to set.

        """
        if self.data is None: # Need to cache calls and do them later
            self.block_cache.append((position, block))
        elif block_types_available:
            self.data.set_block(position, block)

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
        index = int(index)
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
        The block.

        """
        p = position
        x = int(p.x)
        y = int(p.y)
        z = int(p.z)
        proxy = self.get_column(x, y)
        return proxy.get_block(z)

    def set_block(self, position, block):
        """Sets a block in this chunk.
        
        Keyword arguments:
        position -- Position vector. X, Y, Z coordinate form 0-255.
        block -- Block to set.

        """
        p = position
        x = int(p.x)
        y = int(p.y)
        z = int(p.z)
        proxy = self.get_column(x, y)
        proxy.set_block(z, block)

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
        self.__blocks = {} # index -> (block_delta_update)
        self.height = proxy.a + len(proxy) # first not allocated block

    # replaced
    @property
    def a(self):
        return self.__proxy.a

    # replaced
    @property
    def b(self):
        return self.__proxy.b

    # replaced
    def __len__(self):
        return len(self.__proxy)

    # replaced
    def __getitem__(self, index):
        return self.__proxy[index]

    # replaced
    def get_type(self, index):
        return self.__proxy.get_type(index)

    # replaced
    def get_breakable(self, index):
        return self.__proxy.get_breakable(index)

    def get_block(self, z):
        """Absolute block access.
        
        Keyword arguments:
        z -- Absolute z coordinate to access at.

        Returns:
        A block.
        
        """
        if z in self.__blocks:
            return self.__create_block_from_bdu(self.__blocks[z])
        else:
            return self.__create_block_from_native(z)

    def set_block(self, z, block):
        """Absolute block set.
        
        Keyword arguments:
        z -- Absolute z coordinate to write to.
        block -- Block to set.

        """
        if z < self.__proxy.a:
            raise IndexBelowWorldException("Blocks below the a index of a chunk can't be set")

        self.__blocks[z] = self.__create_bdu(block, z)
        if z >= self.height and block.type != EMPTY_TYPE:
            self.height = z + 1
        if z == self.height and block.type == EMPTY_TYPE:
            self.height = self.height - 1
            while self.get_block(self.height).type == EMPTY_TYPE:
                self.height = self.height - 1
            self.height = self.height + 1
        self.__invalidate(z)
        
    def __get_color(self, bdu):
        """Gets the color from a block delta update.
        
        Keyword arguments:
        bdu -- Block delta update.

        """
        return (bdu.color_red, bdu.color_green, bdu.color_blue)

    def __get_type(self, bdu):
        """Gets the type from a block delta update.
        
        Keyword arguments:
        bdu -- Block delta update.

        """
        return bdu.block_type & 0b11111

    def __get_breakable(self, bdu):
        """Gets whether a block is breakable from a block delta update.
        
        Keyword arguments:
        bdu -- Block delta update.

        """
        return (bdu.block_type & 0b00100000) != 0

    def __create_block_from_bdu(self, bdu):
        """Creates a block from a block delta update.
        

        Keyword arguments:
        bdu --  Block delta update.

        """
        color = self.__get_color(bdu)
        type = self.__get_type(bdu)
        breakable = self.__get_breakable(bdu)
        return Block(color, type, breakable)

    def __get_native_color(self, z):
        """Gets the native color of a block.
        
        Keyword arguments:
        z -- Absolute z coordinate.

        """
        a = self.a
        b = self.b
        l = len(self.__proxy)
        if z < b or z >= a + l:
            return (0,0,0)
        elif z >= b and z < a:
            return (128, 128, 128)

        rel_z = z - a
        return self.__proxy[rel_z]

    def __get_native_type(self, z):
        """Gets the native type of a block.
        
        Keyword arguments:
        z -- Absolute z coordinate.

        """
        a = self.a
        b = self.b
        l = len(self.__proxy)
        if z < a:
            return MOUNTAIN_TYPE
        elif z >= a + l:
            if z <= 0:
                return WATER_TYPE
            else:
                return EMPTY_TYPE

        rel_z = z - a
        native_type = self.__proxy.get_type(rel_z)
        if z <= 0 and native_type == EMPTY_TYPE:
            return WATER_TYPE
        return native_type

    def __get_native_breakable(self, z):
        """Gets whether a block is breakable by native.
        
        Keyword arguments:
        z -- Absolute z coordinate.

        """
        a = self.a
        b = self.b
        l = len(self.__proxy)
        if z < a or z >= a + l:
            return False
        
        rel_z = z - a
        return self.__proxy.get_breakable(rel_z)

    def __create_block_from_native(self, z):
        """Creates a block from native values.
        
        Keyword arguments:
        z -- Absolute z coordinate.

        """
        color = self.__get_native_color(z)
        type = self.__get_native_type(z)
        breakable = self.__get_native_breakable(z)
        return Block(color, type, breakable)

    def __create_bdu(self, block, z):
        """Creates a block delta update.
        
        Keyword arguments:
        block -- The block to create it from.
        z -- Absolute z coordinate.

        """
        bdu = BlockDeltaUpdate()
        # All coordinates are specified absolute in block
        # coordinates
        bdu.block_pos = Vector3(self.__x, self.__y, z)
        bdu.color_red, bdu.color_green, bdu.color_blue = block.color
        bdu.block_type = block.type | (block.breakable << 6)
        bdu.something8 = 0
        return bdu
        
    def __invalidate(self, z):
        """Invalidates this block. This means that it will be
        retransferred as soon as possible.
        
        Keyword arguments:
        z -- Absolute z index of block to invalidate.

        """
        cubolt = self.__server.scripts.cubolt
        for con_script in cubolt.children:
            if con_script.is_near(self.__chunk_x, self.__chunk_y):
                bdu = self.__blocks[z]
                if bdu not in con_script.block_deltas:
                    con_script.block_deltas.append(self.__blocks[z])
    
    def _append_deltas(self, deltas):
        """Appends the deltas for this chunk.
        
        Keyword arguments:
        deltas -- List to append to.

        """
        deltas.extend(self.__blocks.values())

class Block:
    def __init__(self, color=(0,0,0), type=EMPTY_TYPE, breakable=False):
        self.color = color
        self.type = type
        self.breakable = breakable