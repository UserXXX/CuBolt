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


from cuwo.entity import FLAGS_FLAG
from cuwo.entity import HOSTILE_FLAG as PACKET_HOSTILE_FLAG
from cuwo.entity import MULTIPLIER_FLAG


from cuwo.constants import HOSTILE_FLAG
from cuwo.constants import FRIENDLY_PLAYER_TYPE


from cuwo.packet import EntityUpdate
from cuwo.packet import HitPacket
from cuwo.packet import HIT_NORMAL


from cuwo.vector import Vector3


MASK_HOSTILITY_SETTING = HOSTILE_FLAG | FLAGS_FLAG | MULTIPLIER_FLAG | PACKET_HOSTILE_FLAG


# TODO: Make init call for other entities than players
class EntityExtension:
    """Class representing an extension for the standard entity class."""
    def __init__(self, entity, manager):
        """Creates a new EntityExtension.
        
        Keyword arguments:
        entity -- The underlying cuwo entity
        manager -- CuBolt entity manager
        
        """
        self._entity = entity
        self._max_hp_multiplier = 100
        self.__joined = False
        self.__manager = manager
        self.__manager._register_entity(self)
    
    # TODO: also call if non player entity is initialized
    def init(self):
        """Initializes this entity."""
        self._max_hp_multiplier = self._entity.max_hp_multiplier
        
    # TODO: also call if non player entity is updated
    def on_entity_update(self, event):
        """Handles an entity update event.
        
        Keyword arguments:
        event -- Event arguments
        
        """
        if not self.__joined:
            self.__joined = True
            self._entity.mask |= MASK_HOSTILITY_SETTING
            self.__manager._update_others(self._entity)
        
        max_hp_multiplier = self._entity.max_hp_multiplier
        if (event.mask & MULTIPLIER_FLAG) != 0 and \
            max_hp_multiplier != _self._max_hp_multiplier:
            self._max_hp_multiplier = max_hp_multiplier
            self.entity.mask |= MULTIPLIER_FLAG
        
    # TODO: also call if non player entity is updated
    def on_flags_update(self, event):
        self._entity.mask |= MASK_HOSTILITY_SETTING
        
    # injected
    def heal(self, amount):
        """Heals this entity.
        
        Keyword arguments:
        amount -- Amount of life to heal
        
        """
        self._entity.damage(-amount)
        
    # injected
    def stun(self, duration):
        """Stuns this entity.
        
        Keyword arguments:
        duration -- Stun duration in ms
        
        """
        self._entity.damage(0, duration)
        
    # injected
    def set_hostility_to(self, entity, hostile, hostility):
        """Sets the hostility of this entity to another and vice
        versa.
        
        Keyword arguments:
        entity -- cuwo entity to set the hostility to
        hostile -- True, for hostile, False for friendly
        hostility -- Hostility mode, see CuBolt constants
        
        """
        m = self.__manager
        m.set_hostility(self._entity, entity, hostile, hostility)
        
    # injected
    def set_hostility_to_id(self, entity_id, hostile, hostility):
        """Sets the hostility of this entity to another and vice
        versa.
        
        Keyword arguments:
        entity_id -- ID of the entity to set the hostility to
        hostile -- True, for hostile, False for friendly
        hostility -- Hostility mode, see CuBolt constants
        
        """
        m = self.__manager
        id = self._entity.entity_id
        m.set_hostility_id(id, entity_id, hostile, hostility)
            
    # injected
    def set_hostility_to_all(self, hostile, hostility):
        """Sets the hostility to all entities.
        
        Keyword arguments:
        hostile -- True, for hostile, False for friendly
        hostility -- Hostility mode, see CuBolt constants
        
        """
        server = self.__manager.server
        for id, entity in server.world.entities.items():
            self.set_hostility_to(entity, hostile, hostility)
    
    # injected
    def destroy(self):
        """Destroys this entity."""
        del self._entity.world.entities[self._entity.entity_id] 
        if not self._entity.static_id: 
            self._entity.world.entity_ids.put_back(self.entity_id) 

        self.__manager._unregister_entity(self)
        
        
class EntityManager:
    """Entity manager for handling hostilities."""
    def __init__(self, server):
        """Creates a new EntityManager.
        
        Keyword arguments:
        server -- Current server instance
        
        """
        self.server = server
        self.default_hostile = False
        self.default_hostility = FRIENDLY_PLAYER_TYPE
        self.__hostilities = {}
        self.__entity_update_packet = EntityUpdate()
        
    def set_hostility(self, entity1, entity2, hostile, hostility):
        """Sets the hostility behaviour between two entities.
        
        Keyword arguments:
        entity1 -- First cuwo entity
        entity2 -- Second cuwo entity
        hostile -- True, if the entities shall be hostile, otherwise
                   False
        hostility -- One of the hostility constants (see
                  cubolt/constants.py)
        
        """
        self.set_hostility_id(entity1.entity_id, entity2.entity_id)
        
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
        for entity in self.server.world.entities.values():
            entity.mask |= MASK_HOSTILITY_SETTING

    def _register_entity(self, entity):
        """Registers an entity and does the main initialization work.
        
        Keyword arguments:
        entity -- CuBolt entity to register
        
        """
        for id, e in self.server.world.entities.items():
            accessor = self.__Set(id, entity._entity.entity_id)
            setting = self.__HostilitySetting(self.default_hostile,
                self.default_hostility)
            self.__hostilities[accessor] = setting
        
        if self.default_hostile:
            entity._entity.flags |= HOSTILE_FLAG
        entity._entity.hostile_type = self.default_hostility
        
    def _unregister_entity(self, entity):
        """Unregisters an entity.
        
        Keyword arguments:
        entity -- CuBolt entity to unregister
        
        """
        for id, e in self.server.world.entities.items():
            if id != entity._entity.entity_id:
                del self.__hostilities[self.__Set(id, entity._entity.entity_id)]
            
                
    def _update_hostility(self, entity):
        """Updates the hostility of an entity. Called from server in
        update routine.
        
        Keyword arguments:
        entity -- cuwo entity to update
        
        """
        hos = self.__hostilities
        for id, e in self.server.world.entities.items():
            if id == entity.entity_id:
                setting = self.__HostilitySetting(False,
                    FRIENDLY_PLAYER_TYPE)
                self.__update_single_hostility(e, entity, setting)
            else:
                h = hos[self.__Set(e.entity_id, entity.entity_id)]
                self.__update_single_hostility(e, entity, h)
       
        self.__clean_up_entity_data(entity)
        
    def _update_others(self, entity):
        """Updates the entity data for all other entities.
        
        Keyword arguments:
        entity -- cuwo entity which data's shall be updated
        
        """
        hos = self.__hostilities
        for id, e in self.server.world.entities.items():
            if id != entity.entity_id:
                h = hos[self.__Set(e.entity_id, entity.entity_id)]
                self.__update_single_hostility(e, entity, h)
                self.__clean_up_entity_data(e)
                
    def __update_single_hostility(self, receiver, sender, hostility):
        """Updates the hostility data of an entity for a single player.
        
        Keyword arguments:
        receiver -- Receiver of the entities data (cuwo entity)
        sender -- Sender thats data shall be transferred (cuwo entity)
        hostility -- Hostility to send
        
        """
        if hostility.hostile:
            sender.flags |= HOSTILE_FLAG
            sender.hostile_type = hostility.hostility
            if hostility.hostility == FRIENDLY_PLAYER_TYPE:
                sender.max_hp_multiplier = \
                    sender.cubolt_entity._max_hp_multiplier
            else:
                sender.max_hp_multiplier = \
                    sender.cubolt_entity._max_hp_multiplier*2.0
        else:
            sender.flags &= ~HOSTILE_FLAG
            sender.hostile_type = FRIENDLY_PLAYER_TYPE
            sender.max_hp_multiplier = sender.cubolt_entity._max_hp_multiplier
        
        entity_update = self.__entity_update_packet
        mask = sender.mask
        entity_update.set_entity(sender,
            sender.entity_id, mask)
        
        players = self.server.players
        if receiver.entity_id in players:
            receiver_con = self.server.players[receiver.entity_id]
            receiver_con.send_packet(entity_update)
    
    def __clean_up_entity_data(self, entity):
        """Cleans up the entities data after sending the data.
        
        Keyword arguments:
        entity -- cuwo entity that's data shall be cleaned up
        
        """
        entity.flags |= HOSTILE_FLAG
        entity.hostile_type = FRIENDLY_PLAYER_TYPE
        mhm = entity.cubolt_entity._max_hp_multiplier
        entity.max_hp_multiplier = mhm
    
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