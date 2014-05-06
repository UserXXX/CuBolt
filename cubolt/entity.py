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
Entity handling.
"""


from cuwo.entity import FLAGS_1_HOSTILE


from cuwo.packet import EntityUpdate
from cuwo.packet import HitPacket
from cuwo.packet import HIT_NORMAL


from cuwo.vector import Vector3


from constants import MASK_HOSTILITY
from constants import MASK_FLAGS
from constants import MASK_MULTIPLIERS
MASK_HOSTILITY_SETTING = MASK_HOSTILITY | MASK_FLAGS | MASK_MULTIPLIERS


from constants import ENTITY_HOSTILITY_FRIENDLY_PLAYER
from constants import ENTITY_HOSTILITY_HOSTILE
from constants import ENTITY_HOSTILITY_FRIENDLY


class Entity:
    def __init__(self):
        self.__max_hp_multiplier = 100
        self.__joined = False
        self.__manager = None
        self.id = -1
        self.data = None
    
    def init(self, entity_id, entity_data, manager):
        self.id = entity_id
        self.data = entity_data
        self._max_hp_multiplier = self.data.max_hp_multiplier
        self.__manager = manager
        self.__manager._register_entity(self)
        
    def damage(self, damage, stun_duration=0):
        packet = HitPacket()
        packet.entity_id = self.id
        packet.target_id = self.id
        packet.hit_type = HIT_NORMAL
        packet.damage = damage
        packet.critical = 1
        packet.stun_duration = stun_duration
        packet.something8 = 0
        packet.pos = self.data.position
        packet.hit_dir = Vector3()
        packet.skill_hit = 0
        packet.show_light = 0
        self.__manager.server.update_packet.player_hits.append(packet)
        
    def heal(self, amount):
        self.damage(-amount)
        
    def kill(self):
        self.damage(self.data.hp + 100.0)
        
    def stun(self, duration):
        self.damage(0, duration)
        
    def set_hostility_to(self, entity, hostile, hostility):
        self.__manager.set_hostility(self, entity, hostile, hostility)
        
    def set_hostility_to_id(self, entity_id, hostile, hostility):
        self.__manager.set_hostility_id(self.id, entity_id, hostile,
            hostility)
            
    def set_hostility_to_all(self, hostile, hostility):
        server = self.__manager.server
        for entity in server.entity_list:
            self.set_hostility_to(entity, hostile, hostility)
    
    def on_unload(self):
        self.__manager._unregister_entity(self)
        
    def on_entity_update(self, event):
        if not self.__joined:
            self.__joined = True
            self.data.mask |= MASK_HOSTILITY_SETTING
            self.__manager._update_others(self)
        
        max_hp_multiplier = self.data.max_hp_multiplier
        if (event.mask & MASK_MULTIPLIERS) != 0 and \
            max_hp_multiplier != _self._max_hp_multiplier:
            self.max_hp = max_hp_multiplier
            self.data.mask |= MASK_MULTIPLIERS
        
    def on_flags_update(self, event):
        self.data.mask |= MASK_HOSTILITY_SETTING
        
        
class EntityManager:
    def __init__(self, server):
        self.server = server
        self.default_hostile = False
        self.default_hostility = ENTITY_HOSTILITY_FRIENDLY_PLAYER
        self.__hostilities = {}
        self.__entity_update_packet = EntityUpdate()
        
    def set_hostility(self, entity1, entity2, hostile, hostility):
        self.set_hostility_id(entity1.id, entity2.id)
        
    def set_hostility_id(self, entity_id_1, entity_id_2, hostile,
        hostility):
        set = self.__Set(entity_id_1, entity_id_2)
        setting = self.__hostilities[set]
        setting.hostile = hostile
        setting.hostility = hostility
        self.server.entities[entity_id_1].mask |= MASK_HOSTILITY_SETTING
        self.server.entities[entity_id_2].mask |= MASK_HOSTILITY_SETTING
        
    def set_hostility_all(self, hostile, hostility):
        for entity_set in self.__hostilities:
            setting = self.__hostilities[entity_set]
            setting.hostile = hostile
            setting.hostility = hostility
        for entity in self.server.entity_list:
            entity.data.mask |= MASK_HOSTILITY_SETTING

    def _register_entity(self, entity):
        for e in self.server.entity_list:
            accessor = self.__Set(e.id, entity.id)
            setting = self.__HostilitySetting(self.default_hostile,
                self.default_hostility)
            self.__hostilities[accessor] = setting
        
        if self.default_hostile:
            entity.data.flags_1 |= FLAGS_1_HOSTILE
        entity.data.hostile_type = self.default_hostility
        
    def _unregister_entity(self, entity):
        for e in self.server.entity_list:
            if e.id != entity.id:
                del self.__hostilities[self.__Set(e.id, entity.id)]
            
                
    def _update_hostility(self, entity): # Called from server in update routine.
        for e in self.server.entity_list:
            if e.id == entity.id:
                setting = self.__HostilitySetting(False,
                    ENTITY_HOSTILITY_FRIENDLY_PLAYER)
                self.__update_single_hostility(e, entity, setting)
            else:
                self.__update_single_hostility(e, entity,
                    self.__hostilities[self.__Set(e.id, entity.id)])
       
        self.__clean_up_entity_data(entity)
        
    def _update_others(self, entity):
        for e in self.server.entity_list:
            if e.id != entity.id:
                self.__update_single_hostility(entity, e,
                    self.__hostilities[self.__Set(e.id, entity.id)])
                self.__clean_up_entity_data(e)
                
    def __update_single_hostility(self, receiver, sender, hostility):
        if hostility.hostile:
            sender.data.flags_1 |= FLAGS_1_HOSTILE
            sender.data.hostile_type = hostility.hostility
            if hostility.hostility == ENTITY_HOSTILITY_FRIENDLY_PLAYER:
                sender.data.max_hp_multiplier = \
                    sender._max_hp_multiplier
            else:
                sender.data.max_hp_multiplier = \
                    sender._max_hp_multiplier*2.0
        else:
            sender.data.flags_1 &= ~FLAGS_1_HOSTILE
            sender.data.hostile_type = ENTITY_HOSTILITY_FRIENDLY_PLAYER
            sender.data.max_hp_multiplier = sender._max_hp_multiplier
        
        entity_update = self.__entity_update_packet
        mask = sender.data.mask
        entity_update.set_entity(sender.data,
            sender.id, mask)
        
        players = self.server.players
        if receiver.id in players:
            receiver_con = self.server.players[receiver.id]
            receiver_con.send_packet(entity_update)
    
    def __clean_up_entity_data(self, entity):
        entity.data.flags_1 |= FLAGS_1_HOSTILE
        entity.data.hostile_type = ENTITY_HOSTILITY_FRIENDLY_PLAYER
        entity.data.max_hp_multiplier = entity._max_hp_multiplier
    
    class __Set:
        def __init__(self, t1, t2):
            self.t1 = t1
            self.t2 = t2
            self.__hash = hash(t1) + hash(t2)
        
        def __hash__(self):
            return self.__hash
        
        def __eq__(self, other):
            return (self.t1 == other.t1 and self.t2 == other.t2) or \
                (self.t1 == other.t2 and self.t2 == other.t1)
    
    class __HostilitySetting:
        def __init__(self, hostile, hostility):
            self.hostile = hostile
            self.hostility = hostility