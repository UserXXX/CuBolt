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


"""Entity handling."""

from cuwo.entity import HOSTILE_FLAG


from cuwo.packet import EntityUpdate
from cuwo.packet import HitPacket
from cuwo.packet import HIT_NORMAL


from cuwo.vector import Vector3


from .constants import MASK_HOSTILITY
from .constants import MASK_FLAGS
from .constants import MASK_MULTIPLIERS
MASK_HOSTILITY_SETTING = MASK_HOSTILITY | MASK_FLAGS | MASK_MULTIPLIERS


from .constants import ENTITY_HOSTILITY_FRIENDLY_PLAYER
from .constants import ENTITY_HOSTILITY_HOSTILE
from .constants import ENTITY_HOSTILITY_FRIENDLY


class Entity:
    """Class representing a CuBolt entity."""
    def __init__(self):
        """Creates a new entity."""
        self.__max_hp_multiplier = 100
        self.__joined = False
        self.__manager = None
        self.id = -1
        self.data = None
    
    def init(self, entity_id, entity_data, manager):
        """Initializes this entity.
        
        Keyword arguments:
        entity_id -- Entity ID
        entity_data -- Entity data
        manager -- CuBolt entity manager
        
        """
        self.id = entity_id
        self.data = entity_data
        self._max_hp_multiplier = self.data.max_hp_multiplier
        self.__manager = manager
        self.__manager._register_entity(self)
        
    def damage(self, damage, stun_duration=0):
        """Damages this entity.
        
        Keyword arguments:
        damage -- Amount of damage to deal
        stun_duration -- Duration of the stun in ms
        
        """
        packet = HitPacket()
        packet.entity_id = self.id
        packet.target_id = self.id
        packet.hit_type = HIT_NORMAL
        packet.damage = damage
        packet.critical = 1
        packet.stun_duration = stun_duration
        packet.something8 = 0
        packet.pos = self.data.pos
        packet.hit_dir = Vector3()
        packet.skill_hit = 0
        packet.show_light = 0
        self.__manager.server.update_packet.player_hits.append(packet)
        
    def heal(self, amount):
        """Heals this entity.
        
        Keyword arguments:
        amount -- Amount of life to heal
        
        """
        self.damage(-amount)
        
    def kill(self):
        """Kills this entity."""
        self.damage(self.data.hp + 100.0)
        
    def stun(self, duration):
        """Stuns this entity.
        
        Keyword arguments:
        duration -- Stun duration in ms
        
        """
        self.damage(0, duration)
        
    def set_hostility_to(self, entity, hostile, hostility):
        """Sets the hostility of this entity to another and vice
        versa.
        
        Keyword arguments:
        entity -- Entity to set the hostility to
        hostile -- True, for hostile, False for friendly
        hostility -- Hostility mode, see CuBolt constants
        
        """
        self.__manager.set_hostility(self, entity, hostile, hostility)
        
    def set_hostility_to_id(self, entity_id, hostile, hostility):
        """Sets the hostility of this entity to another and vice
        versa.
        
        Keyword arguments:
        entity_id -- ID of the entity to set the hostility to
        hostile -- True, for hostile, False for friendly
        hostility -- Hostility mode, see CuBolt constants
        
        """
        self.__manager.set_hostility_id(self.id, entity_id, hostile,
            hostility)
            
    def set_hostility_to_all(self, hostile, hostility):
        """Sets the hostility to all entities.
        
        Keyword arguments:
        hostile -- True, for hostile, False for friendly
        hostility -- Hostility mode, see CuBolt constants
        
        """
        server = self.__manager.server
        for id, entity in server.entity_list.items():
            self.set_hostility_to(entity, hostile, hostility)
    
    def on_unload(self):
        """Unloads this entity."""
        self.__manager._unregister_entity(self)
        
    def on_entity_update(self, event):
        """Handles an entity update event.
        
        Keyword arguments:
        event -- Event arguments
        
        """
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
    """Entity manager for handling hostilities."""
    def __init__(self, server):
        """Creates a new EntityManager.
        
        Keyword arguments:
        server -- Current server instance
        
        """
        self.server = server
        self.default_hostile = False
        self.default_hostility = ENTITY_HOSTILITY_FRIENDLY_PLAYER
        self.__hostilities = {}
        self.__entity_update_packet = EntityUpdate()
        
    def set_hostility(self, entity1, entity2, hostile, hostility):
        """Sets the hostility behaviour between two entities.
        
        Keyword arguments:
        entity1 -- First entity
        entity2 -- Second entity
        hostile -- True, if the entities shall be hostile, otherwise
                   False
        hostility -- One of the hostility constants (see
                  cubolt/constants.py)
        
        """
        self.set_hostility_id(entity1.id, entity2.id)
        
    def set_hostility_id(self, entity_id_1, entity_id_2, hostile,
        hostility):
        """Sets the hostility behaviour between two entities.
        
        Keyword arguments:
        entity_id_1 -- First entity id
        entity_id_2 -- Second entity id
        hostile -- True, if the entities shall be hostile, otherwise
                   False
        hostility -- One of the hostility constants (see
                  cubolt/constants.py)
        
        """
        # players currently seem to be the only entities...
        if entity_id_1 != entity_id_2: 
            set = self.__Set(entity_id_1, entity_id_2)
            setting = self.__hostilities[set]
            setting.hostile = hostile
            setting.hostility = hostility
            entity1 = self.server.players[entity_id_1].entity
            entity1.mask |= MASK_HOSTILITY_SETTING
            entity2 = self.server.players[entity_id_2].entity
            entity2.mask |= MASK_HOSTILITY_SETTING
        
    def set_hostility_all(self, hostile, hostility):
        """Sets the hostility behaviour between all entities.
        
        Keyword arguments:
        hostile -- True, if the entities shall be hostile, otherwise
                   False
        hostility -- One of the hostility constants (see
                  cubolt/constants.py)
        
        """
        for entity_set in self.__hostilities:
            setting = self.__hostilities[entity_set]
            setting.hostile = hostile
            setting.hostility = hostility
        # players currently seem to be the only entities...
        for player in self.server.players.values():
            player.entity.mask |= MASK_HOSTILITY_SETTING

    def _register_entity(self, entity):
        """Registers an entity and does the main initialization work.
        
        Keyword arguments:
        entity -- Entity to register
        
        """
        for id, e in self.server.entity_list.items():
            accessor = self.__Set(e.id, entity.id)
            setting = self.__HostilitySetting(self.default_hostile,
                self.default_hostility)
            self.__hostilities[accessor] = setting
        
        if self.default_hostile:
            entity.data.flags |= HOSTILE_FLAG
        entity.data.hostile_type = self.default_hostility
        
    def _unregister_entity(self, entity):
        """Unregisters an entity.
        
        Keyword arguments:
        entity -- Entity to unregister
        
        """
        for id, e in self.server.entity_list.items():
            if e.id != entity.id:
                del self.__hostilities[self.__Set(e.id, entity.id)]
            
                
    def _update_hostility(self, entity):
        """Updates the hostility of an entity. Called from server in
        update routine.
        
        Keyword arguments:
        entity -- Entity to update
        
        """
        for id, e in self.server.entity_list.items():
            if e.id == entity.id:
                setting = self.__HostilitySetting(False,
                    ENTITY_HOSTILITY_FRIENDLY_PLAYER)
                self.__update_single_hostility(e, entity, setting)
            else:
                self.__update_single_hostility(e, entity,
                    self.__hostilities[self.__Set(e.id, entity.id)])
       
        self.__clean_up_entity_data(entity)
        
    def _update_others(self, entity):
        """Updates the entity data for all other entities.
        
        Keyword arguments:
        entity -- Entity which data's shall be updated
        
        """
        for id, e in self.server.entity_list.items():
            if e.id != entity.id:
                self.__update_single_hostility(entity, e,
                    self.__hostilities[self.__Set(e.id, entity.id)])
                self.__clean_up_entity_data(e)
                
    def __update_single_hostility(self, receiver, sender, hostility):
        """Updates the hostility data of an entity for a single player.
        
        Keyword arguments:
        receiver -- Receiver of the entities data
        sender -- Sender thats data shall be transferred
        hostility -- Hostility to send
        
        """
        if hostility.hostile:
            sender.data.flags |= HOSTILE_FLAG
            sender.data.hostile_type = hostility.hostility
            if hostility.hostility == ENTITY_HOSTILITY_FRIENDLY_PLAYER:
                sender.data.max_hp_multiplier = \
                    sender._max_hp_multiplier
            else:
                sender.data.max_hp_multiplier = \
                    sender._max_hp_multiplier*2.0
        else:
            sender.data.flags &= ~HOSTILE_FLAG
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
        """Cleans up the entities data after sending the data.
        
        Keyword arguments:
        entity -- Entity that's data shall be cleaned up
        
        """
        entity.data.flags |= HOSTILE_FLAG
        entity.data.hostile_type = ENTITY_HOSTILITY_FRIENDLY_PLAYER
        entity.data.max_hp_multiplier = entity._max_hp_multiplier
    
    class __Set:
        """Private class for storing the hostility settings between
        entities.
        
        """
        def __init__(self, t1, t2):
            """Creates a new Set.
            
            Keyword arguments:
            t1 -- First data blob
            t2 -- Second data blob
            
            """
            self.t1 = t1
            self.t2 = t2
            self.__hash = hash(t1) + hash(t2)
        
        def __hash__(self):
            """Returns the calculated hash."""
            return self.__hash
        
        def __eq__(self, other):
            """Checks if another object is equal to this one."""
            return (self.t1 == other.t1 and self.t2 == other.t2) or \
                (self.t1 == other.t2 and self.t2 == other.t1)
    
    class __HostilitySetting:
        """Private class for storing hostility settings."""
        def __init__(self, hostile, hostility):
            """Creates a new HostilitySetting.
            
            hostile -- True, if the regarding entities are hostile,
                       otherwise False.
            hostility -- One of the hostility constants (see
                  cubolt/constants.py)
                  
            """
            self.hostile = hostile
            self.hostility = hostility