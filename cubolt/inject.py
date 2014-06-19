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


"""
Code injected into cuwo.
"""


from cuwo.packet import CurrentTime
from cuwo.packet import UpdateFinished


from cuwo.loop import LoopingCall


try:
    from .particle import ParticleEffect
    has_particles = True
except:
    has_particles = False
from .util import Color

class Injector(object):
    def __init__(self, server):
        self.server = server
        if not has_particles:
            print(('The particles module could not be loaded. Are ' + 
                'you using an old cuwo version?'))

    def inject_update(self):
        self.update_finished_packet = UpdateFinished()
        self.time_packet = CurrentTime()
        
        self.server.update = self.update
        self.server.update_loop.func = self.server.update
    
    # Replaces the default update algorithm in server.py #
    def update(self):
        s = self.server

        s.scripts.call('update')

        # entity updates
        # The client doesn't allow friendly display and hostile
        # behaviour, so have a little workaround...
        em = s.entity_manager
        for id, entity in s.entity_list.items():
            em._update_hostility(entity)
            entity.data.mask = 0 
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
    
    def inject_particle_factory(self):
        if has_particles:
            s = self.server
            s.create_particle_effect = self.create_particle_effect
    
    def create_particle_effect(self):
        return ParticleEffect(self.server)
        
    def inject_color_factory(self):
        s = self.server
        s.create_color = self.create_color
        
    def create_color(self, red=1.0, green=1.0, blue=1.0, alpha=1.0):
        return Color(red, green, blue, alpha)