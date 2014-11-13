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


"""Constants."""


# Bitmasks for entity update packets.
MASK_HOSTILITY = 1 << 7
MASK_FLAGS = 1 << 14
MASK_MULTIPLIERS = 1 << 30


# Entity hostility settings
ENTITY_HOSTILITY_FRIENDLY_PLAYER = 0
ENTITY_HOSTILITY_HOSTILE = 1
ENTITY_HOSTILITY_FRIENDLY = 2


# Particle modes
PARTICLES_SOLID = 0
PARTICLES_BOMB = 1
PARTICLES_NO_ACCELLERATION = 3
PARTICLES_NO_GRAVITY = 4

# Block type constants
BLOCK_TYPE_EMPTY = 0
BLOCK_TYPE_WATER = 2
BLOCK_TYPE_WATER2 = 3
BLOCK_TYPE_GRASS = 4
BLOCK_TYPE_MOUNTAIN = 6
BLOCK_TYPE_TREE = 8