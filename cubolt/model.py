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


"""Model handling."""


import sqlite3
import os.path
import struct

from cuwo.bytes import ByteReader
from cuwo.cub import CubModel
from cuwo.world import World
from cuwo.vector import Vector3

try:
    from cuwo.tgen import MOUNTAIN_TYPE
    block_types_available = True
except ImportError:
    MOUNTAIN_TYPE = 6
    block_types_available = False

from .world import Block
    

MODEL_DATABASE = os.path.join('data', 'data1.db')


OFFSET_LOOKUP_TABLE = [0x1092, 0x254F, 0x348, 0x14B40, 0x241A, 0x2676,
                       0x7F, 0x9, 0x250B, 0x18A, 0x7B, 0x12E2, 0x7EBC,
                       0x5F23, 0x981, 0x11, 0x85BA, 0x0A566, 0x1093,
                       0x0E, 0x2D266, 0x7C3, 0x0C16, 0x76D, 0x15D41,
                       0x12CD, 0x25, 0x8F, 0x0DA2, 0x4C1B, 0x53F,
                       0x1B0, 0x14AFC, 0x23E0, 0x258C, 0x4D1, 0x0D6A,
                       0x72F, 0x0BA8, 0x7C9, 0x0BA8, 0x131F, 0x0C75C7,
                       0x0D]

    
class ByteArrayReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
    
    def read_uint32(self):
        result = self.data[self.pos]
        self.pos = self.pos + 1
        result = result | self.data[self.pos] << 8
        self.pos = self.pos + 1
        result = result | self.data[self.pos] << 16
        self.pos = self.pos + 1
        result = result | self.data[self.pos] << 24
        self.pos = self.pos + 1
        return result
        
    def read_uint8(self):
        self.pos = self.pos + 1
        return self.data[self.pos - 1]
    

class Model:
    """Base class for all loadable models."""
    def __init__(self, server):
        """Creates a new model.
        
        Keyword arguments:
        server -- Server instance.

        """
        self.server = server

    def place_in_world_v(self, lower_pos, type=MOUNTAIN_TYPE, breakable=False,
                         remove_blocks=False):
        """Places the model in the world.

        Keyword arguments:
        lower_pos -- Position where to start placing blocks.
        type -- Block type to use for placed blocks.
        remove_blocks -- True to remove all blocks within the models
            bounds that are not part of it.

        """
        x = int(lower_pos.x)
        y = int(lower_pos.y)
        z = int(lower_pos.z)
        self.place_in_world(x, y, z, type, breakable, remove_blocks)

    def place_in_world(self, lower_x, lower_y, lower_z,
                       type=MOUNTAIN_TYPE, breakable=False,
                       remove_blocks=False):
        """Places the model in the world.

        Keyword arguments:
        lower_x -- X coordinate where to start placing the blocks.
        lower_y -- Y coordinate where to start placing the blocks.
        lower_z -- Z coordinate where to start placing the blocks.
        type -- Block type to use for placed blocks.
        remove_blocks -- True to remove all blocks within the models
            bounds that are not part of it.

        """
        w = self.server.world
        if remove_blocks:
            size = self.size
            size_x = int(size.x)
            size_y = int(size.y)
            size_z = int(size.z)
            for x in range(0, size_x):
                for y in range(0, size_y):
                    for z in range(0, size_z):
                        pos = (x,y,z)
                        pos_v = Vector3(x, y, z)
                        if pos in self.data:
                            c = self.data[pos]
                            w.set_block(pos_v, Block(c,type))
                        else:
                            w.set_block(pos_v, Block())
        else:
            for pos in self.data.keys():
                x = pos[0] + lower_x
                y = pos[1] + lower_y
                z = pos[2] + lower_z
                color = self.data[pos]
                w.set_block(Vector3(x, y, z), Block(color,type))
 
    def rotate_left_z(self):
        """Rotates the model for 90 degrees to the left around the
        z-axis.
        
        """
        new_data = {}
        max_index_y = int(self.size.y) - 1
        for pos in self.data.keys():
            new_pos = (max_index_y - pos[1], pos[0], pos[2])
            new_data[new_pos]  = self.data[pos]
        self.data = new_data
        tmp = self.size.x
        self.size.x = self.size.y
        self.size.y = tmp

    def rotate_right_z(self):
        """Rotates the model for 90 degrees to the right around the
        z-axis.
        
        """
        new_data = {}
        max_index_x = int(self.size.x) - 1
        for pos in self.data.keys():
            new_pos = (pos[1], max_index_x - pos[0], pos[2])
            new_data[new_pos]  = self.data[pos]
        self.data = new_data
        tmp = self.size.x
        self.size.x = self.size.y
        self.size.y = tmp

    def rotate_180_z(self):
        """Rotates the model for 180 degrees to the right around the
        z-axis.
        
        """
        new_data = {}
        max_index_x = int(self.size.x) - 1
        max_index_y = int(self.size.y) - 1
        for pos in self.data.keys():
            x = max_index_x - pos[0]
            y = max_index_y - pos[1]
            new_pos = (x, y, pos[2])
            new_data[new_pos]  = self.data[pos]
        self.data = new_data

    def mirror_x(self):
        """Mirrors the model at the x-axis."""
        new_data = {}
        max_index_y = int(self.size.y) - 1
        for pos in self.data.keys():
            new_pos = (pos[0], max_index_y - pos[1], pos[2])
            new_data[new_pos]  = self.data[pos]
        self.data = new_data

    def mirror_y(self):
        """Mirrors the model at the y-axis."""
        new_data = {}
        max_index_x = self.size.x - 1
        for pos in self.data.keys():
            new_pos = (max_index_x - pos[0], pos[1], pos[2])
            new_data[new_pos]  = self.data[pos]
        self.data = new_data
        tmp = self.size.x
        self.size.x = self.size.y
        self.size.y = tmp

 
class CubeModel(Model):
    """Model class for Cube Worlds default Models (*.cub files)."""
    def __init__(self, server, filename, from_database=False):
        """Creates a new model.
        
        Keyword arguments:
        server -- Server instance.
        filename -- Name of the file to load.
        from_database -- True, to load from the default data1.db file,
            False to load the file from disk.

        """
        Model.__init__(self, server)
        if from_database:
            db_connection = sqlite3.connect(MODEL_DATABASE)
            cursor = db_connection.cursor()
            cursor.execute('SELECT * FROM blobs WHERE key=?',
                [filename])
            row = cursor.fetchone()
            model_data = bytearray(row[1])
            model_data = self.__descramble(model_data)
            model = CubModel(ByteArrayReader(model_data))
            x = model.x_size
            y = model.y_size
            z = model.z_size
            self.size = Vector3(x, y, z)
            self.data = model.blocks
        else:
            model = CubModel(ByteReader(open(filename, 'rb').read()))
            x = model.x_size
            y = model.y_size
            z = model.z_size
            self.size = Vector3(x, y, z)
            self.data = model.blocks
            
    def __descramble(self, model_data):
        data_len = len(model_data)
        
        for i in range(data_len - 1, -1, -1):
            offset = (i + OFFSET_LOOKUP_TABLE[i % 44]) % data_len

            temp = model_data[i]
            model_data[i] = model_data[offset]
            model_data[offset] = temp

        for i in range(0, data_len):
            model_data[i] = ~(model_data[i]) + 256
            
        return model_data