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


from twisted.internet.task import LoopingCall


class Injector:
    def inject_update(self, server):
        self.server_instance = server
        self.update_finished_packet = UpdateFinished()
        self.time_packet = CurrentTime()
        
        server.update = self.update
        server.update_loop.f = server.update
    
    # Replaces the default update algorithm in server.py #
    def update(self):
        s = self.server_instance

        s.scripts.call('update')

        # entity updates
        # The client doesn't allow friendly display and hostile
        # behaviour, so have a little workaround...
        em = s.entity_manager
        for id, entity in s.entity_list.iteritems():
            em._update_hostility(entity)
            entity.data.mask = 0 
        s.broadcast_packet(self.update_finished_packet)

        # other updates
        update_packet = s.update_packet
        if s.items_changed:
            for chunk, items in s.chunk_items.iteritems():
                item_list = ChunkItems()
                item_list.chunk_x, item_list.chunk_y = chunk
                item_list.items = items
                update_packet.chunk_items.append(item_list)
        s.broadcast_packet(update_packet)
        update_packet.reset()

        # reset drop times
        if s.items_changed:
            for items in s.chunk_items.values():
                for item in items:
                    item.drop_time = 0
            s.items_changed = False

        # time update
        self.time_packet.time = s.get_time()
        self.time_packet.day = s.get_day()
        s.broadcast_packet(self.time_packet)