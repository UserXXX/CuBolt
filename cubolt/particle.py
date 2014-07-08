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


"""Particle effects."""


import time


from cuwo.packet import ParticleData
from cuwo.vector import Vector3


from .constants import PARTICLES_SOLID
from .util import Color


class ParticleEffect:
    """Class for managing particle effects."""
    def __init__(self, server):
        """Creates a new particle effect.
        
        Keyword arguments:
        server -- Server instance
        
        """
        self.server = server
        self.interval = None
        self.__counter = time.time()
        
        self.data = ParticleData()
        self.data.pos = Vector3(0.0, 0.0, 0.0)
        self.data.accel = Vector3(0.0, 0.0, 0.0)
        self.data.color_red = 1.0
        self.data.color_blue = 1.0
        self.data.color_green = 1.0
        self.data.color_alpha = 1.0
        self.data.scale = 1.0
        self.data.count = 100
        self.data.particle_type = PARTICLES_SOLID
        self.data.spreading = 1.0
        self.data.something18 = 0
    
    def update(self):
        """Updates the particle effect if an interval is set."""
        if self.interval is not None:
            t = time.time()
            difference = t - self.__counter
            if difference > self.interval:
                self.__counter = t - difference + self.interval
                self.fire()
                
    def fire(self):
        """Fires the particle effect."""
        self.server.update_packet.particles.append(self.data)