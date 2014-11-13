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


"""Model handling."""


import sqlite3
import os.path
import struct


from cuwo.bytes import ByteReader
from cuwo.cub import CubModel


try:
    from cuwo.world import World
    has_world = True
except ImportError:
    has_world = False


from .constants import BLOCK_TYPE_MOUNTAIN
    

MODEL_DATABASE = os.path.join('data', 'data1.db')


OFFSET_LOOKUP_TABLE = [0x1092, 0x254F, 0x348, 0x14B40, 0x241A, 0x2676,
    0x7F, 0x9, 0x250B, 0x18A, 0x7B, 0x12E2, 0x7EBC, 0x5F23, 0x981,
    0x11, 0x85BA, 0x0A566, 0x1093, 0x0E, 0x2D266, 0x7C3, 0x0C16,
    0x76D, 0x15D41, 0x12CD, 0x25, 0x8F, 0x0DA2, 0x4C1B, 0x53F, 0x1B0,
    0x14AFC, 0x23E0, 0x258C, 0x4D1, 0x0D6A, 0x72F, 0x0BA8, 0x7C9,
    0x0BA8, 0x131F, 0x0C75C7, 0x0D]

    
class ByteArrayReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
    
    def read_uint32(self):
        result = self.data[self.pos] << 24
        self.pos = self.pos + 1
        result = result | self.data[self.pos] << 16
        self.pos = self.pos + 1
        result = result | self.data[self.pos] << 8
        self.pos = self.pos + 1
        result = result | self.data[self.pos]
        self.pos = self.pos + 1
        return result
        
    def read_uint_8(self):
        self.pos = self.pos + 1
        return self.data[self.pos - 1]
    

class Model:
    def __init__(self, server):
        self.server = server

    def place_in_world(self, lower_x, lower_y, lower_z):
        if not has_world or not self.server.config.base.use_world:
            raise NameError(('[CB] The world module could not be' +
                ' loaded.'))
        
        server = self.server
        for pos in self.data.keys():
            x = pos[0] + lower_x
            y = pos[1] + lower_y
            z = pos[2] + lower_z
            block = server.get_block(x, y, z)
            print('Got block!')
            color = self.data[pos]
            block.r = color[0]
            block.g = color[1]
            block.b = color[2]
            block.type = BLOCK_TYPE_MOUNTAIN
 
 
class CubeModel(Model):
    def __init__(self, server, filename, from_database=False):
        Model.__init__(self, server)
        if from_database:
            db_connection = sqlite3.connect(MODEL_DATABASE)
            cursor = db_connection.cursor()
            cursor.execute('SELECT * FROM blobs WHERE key=?',
                [filename])
            row = cursor.fetchone()
            model_data = row[1]
            model_data = self.__descramble(model_data)
            model = CubModel(ByteArrayReader(model_data))
            self.size_x = model.x_size
            self.size_y = model.y_size
            self.size_z = model.z_size
            self.data = model.blocks
        else:
            model = CubModel(ByteReader(open(filename, 'rb').read()))
            self.size_x = model.x_size
            self.size_y = model.y_size
            self.size_z = model.z_size
            self.data = model.blocks
            
    def __descramble(self, model_data):
        ret = []
        for m in model_data:
            ret.append(m)
    
        currOff = len(ret) - 1
        while currOff >= 0:
            offset = (currOff + OFFSET_LOOKUP_TABLE[currOff % 44]) % \
                len(ret)
                
            temp = ret[currOff]
            ret[currOff] = ret[offset]
            ret[offset] = temp
            
            currOff = currOff - 1
        
        i = 0
        while i < len(ret):
            ret[i] = -1 - ret[i];
            i = i + 1
            
        return ret