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


"""World handling."""


import sqlite3
import os.path


from cuwo.vector import Vector3


from .constants import BLOCK_TYPE_EMPTY
from .constants import BLOCK_TYPE_MOUNTAIN


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