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


"""Entity handling."""


from cuwo.constants import HOSTILE_FLAG
from cuwo.constants import FRIENDLY_PLAYER_TYPE
from cuwo.constants import FRIENDLY_TYPE
from cuwo.constants import HOSTILE_TYPE
from cuwo.constants import FULL_MASK
from cuwo.entity import FLAGS_FLAG
from cuwo.entity import HOSTILE_FLAG as PACKET_HOSTILE_FLAG
from cuwo.entity import MULTIPLIER_FLAG
from cuwo.entity import POS_FLAG
from cuwo.packet import EntityUpdate
from cuwo.packet import HitPacket
from cuwo.packet import HIT_NORMAL
from cuwo.static import StaticEntityPacket
from cuwo.static import StaticEntityHeader
from cuwo.static import ORIENT_SOUTH
from cuwo.vector import Vector3

from .constants import RELATION_FRIENDLY_PLAYER
from .constants import RELATION_FRIENDLY
from .constants import RELATION_FRIENDLY_NAME
from .constants import RELATION_HOSTILE_PLAYER
from .constants import RELATION_HOSTILE
from .constants import RELATION_NEUTRAL
from .constants import RELATION_TARGET


FRIENDLY_TYPE_NAME = 3
FRIENDLY_TYPE_2 = 4
FRIENDLY_TYPE_3 = 5
TARGET_TYPE = 6
# Everything larger than 6 seems to be same as FRIENDLY_TYPE


RELATION_HOSTILE_TYPE_MAPPING = {
    RELATION_FRIENDLY_PLAYER : FRIENDLY_PLAYER_TYPE,
    RELATION_FRIENDLY : FRIENDLY_TYPE,
    RELATION_FRIENDLY_NAME : FRIENDLY_TYPE_NAME,
    RELATION_HOSTILE_PLAYER : FRIENDLY_PLAYER_TYPE,
    RELATION_HOSTILE : HOSTILE_TYPE,
    RELATION_NEUTRAL : FRIENDLY_TYPE,
    RELATION_TARGET : TARGET_TYPE,
}


NATIVE_SETTING_MAPPING = {
    FRIENDLY_PLAYER_TYPE : {
        FRIENDLY_PLAYER_TYPE : RELATION_FRIENDLY_PLAYER,
        FRIENDLY_TYPE : RELATION_FRIENDLY,
        HOSTILE_TYPE : RELATION_HOSTILE,

        FRIENDLY_TYPE_NAME : RELATION_FRIENDLY_NAME,
        FRIENDLY_TYPE_2 : RELATION_FRIENDLY,
        FRIENDLY_TYPE_3 : RELATION_FRIENDLY,
        TARGET_TYPE : RELATION_TARGET,
    },
    
    FRIENDLY_TYPE : {
        FRIENDLY_PLAYER_TYPE : RELATION_FRIENDLY_PLAYER,
        FRIENDLY_TYPE : RELATION_FRIENDLY,
        HOSTILE_TYPE : RELATION_HOSTILE,

        FRIENDLY_TYPE_NAME : RELATION_FRIENDLY_NAME,
        FRIENDLY_TYPE_2 : RELATION_FRIENDLY,
        FRIENDLY_TYPE_3 : RELATION_FRIENDLY,
        TARGET_TYPE : RELATION_TARGET,
    },
    
    HOSTILE_TYPE : {
        FRIENDLY_PLAYER_TYPE : RELATION_HOSTILE_PLAYER,
        FRIENDLY_TYPE : RELATION_HOSTILE,
        HOSTILE_TYPE : RELATION_FRIENDLY,

        FRIENDLY_TYPE_NAME : RELATION_HOSTILE,
        FRIENDLY_TYPE_2 : RELATION_HOSTILE,
        FRIENDLY_TYPE_3 : RELATION_HOSTILE,
        TARGET_TYPE : RELATION_TARGET,
    },

    FRIENDLY_TYPE_NAME : {
        FRIENDLY_PLAYER_TYPE : RELATION_FRIENDLY_PLAYER,
        FRIENDLY_TYPE : RELATION_FRIENDLY,
        HOSTILE_TYPE : RELATION_HOSTILE,

        FRIENDLY_TYPE_NAME : RELATION_FRIENDLY_NAME,
        FRIENDLY_TYPE_2 : RELATION_FRIENDLY,
        FRIENDLY_TYPE_3 : RELATION_FRIENDLY,
        TARGET_TYPE : RELATION_TARGET,
    },
    
    FRIENDLY_TYPE_2 : {
        FRIENDLY_PLAYER_TYPE : RELATION_FRIENDLY_PLAYER,
        FRIENDLY_TYPE : RELATION_FRIENDLY,
        HOSTILE_TYPE : RELATION_HOSTILE,

        FRIENDLY_TYPE_NAME : RELATION_FRIENDLY_NAME,
        FRIENDLY_TYPE_2 : RELATION_FRIENDLY,
        FRIENDLY_TYPE_3 : RELATION_FRIENDLY,
        TARGET_TYPE : RELATION_TARGET,
    },

    FRIENDLY_TYPE_3 : {
        FRIENDLY_PLAYER_TYPE : RELATION_FRIENDLY_PLAYER,
        FRIENDLY_TYPE : RELATION_FRIENDLY,
        HOSTILE_TYPE : RELATION_HOSTILE,

        FRIENDLY_TYPE_NAME : RELATION_FRIENDLY_NAME,
        FRIENDLY_TYPE_2 : RELATION_FRIENDLY,
        FRIENDLY_TYPE_3 : RELATION_FRIENDLY,
        TARGET_TYPE : RELATION_TARGET,
    },

    TARGET_TYPE : {
        FRIENDLY_PLAYER_TYPE : RELATION_FRIENDLY_PLAYER,
        FRIENDLY_TYPE : RELATION_FRIENDLY,
        HOSTILE_TYPE : RELATION_HOSTILE,

        FRIENDLY_TYPE_NAME : RELATION_FRIENDLY_NAME,
        FRIENDLY_TYPE_2 : RELATION_FRIENDLY,
        FRIENDLY_TYPE_3 : RELATION_FRIENDLY,
        TARGET_TYPE : RELATION_TARGET,
    },
}


MASK_HOSTILITY_SETTING = HOSTILE_FLAG | FLAGS_FLAG | MULTIPLIER_FLAG | PACKET_HOSTILE_FLAG


class EntityExtension:
    """Class representing an extension for the standard entity class."""

    def __init__(self, entity, server):
        """Creates a new EntityExtension.
        
        Keyword arguments:
        entity -- The underlying cuwo entity
        
        """
        self._entity = entity
        self.__server = server
        self._max_hp_multiplier = 1
        self.__initialized = False
        # Non standard hostilities are saved here in form: <entity id:relation> 
        self.__relation_to = {}
        self.__entity_update_packet = EntityUpdate()
    
    def __init(self):
        """Initializes this entity. Only called if this entity is a player."""
        self._native_hostile_type = self._entity.hostile_type
        self._native_max_hp_multiplier = self._entity.max_hp_multiplier
        # perform complete update, this is the initial data transfer
        self._entity.mask = FULL_MASK
        
        # get connection script for this entity
        con_scripts = self.__server.scripts.cubolt.children
        entity = self._entity
        for script in con_scripts:
            if script.connection.entity == entity:
                self.__con_script = script
                break

        self.__initialized = True
        
    def on_entity_update(self, event):
        """Handles an entity update event.
        
        Keyword arguments:
        event -- Event arguments
        
        """
        if not self.__initialized:
            self.__init()
        
        # If client send an multiplier update, check if the 
        # max_hp_multiplayer has been updated. If so, there is
        # a new native max_hp_multiplier and we need to re-send
        # the calculated one.
        max_hp_multiplier = self._entity.max_hp_multiplier
        if (event.mask & MULTIPLIER_FLAG) != 0 and \
            max_hp_multiplier != self._native_max_hp_multiplier:
            self._native_max_hp_multiplier = max_hp_multiplier
            self.entity.mask |= MULTIPLIER_FLAG
        
    def get_hostile_type_by_relation(self, relation):
        """Gets the hostile type for a specified relation.
        
        Keyword arguments:
        relation -- Relation constant.
        
        Returns:
        One of the hostility types from cuwo.constants
        
        """
        return RELATION_HOSTILE_TYPE_MAPPING[relation]
        
    def get_mask_extension_by_relation(self, relation):
        """Gets the mask for a specified relation.
        
        Keyword arguments:
        relation -- Relation constant.
        
        Returns:
        The flag extension for the specified relation.
        
        """
        if relation > RELATION_FRIENDLY:
            return PACKET_HOSTILE_FLAG
        else:
            return 0
    
    def get_max_hp_multiplier_by_relation(self, relation):
        """Gets the max_hp_multiplier to use for an entity that shall
        have the specified relation.
        
        Keyword arguments:
        relation -- Relation to display.
        
        Returns:
        The calculated max_hp_multiplier.
        
        """
        if not self.__initialized:
            return 1
        else:
            native_hostile_type = self._native_hostile_type
            native_max_hp_multiplier = self._native_max_hp_multiplier
            hos_type = self.get_hostile_type_by_relation(relation)
            if hos_type == native_hostile_type:
                return native_max_hp_multiplier
            elif self.is_npc():
                if hos_type == FRIENDLY_PLAYER_TYPE:
                    # NPC and FRIENDlY_PLAYER setting, so it is neccassary to
                    # adjust the hp multiplier. Reduce it to power_health.
                    power_health = 2 ** (self._entity.power_base * 0.25)
                    return (power_health / 2) * native_max_hp_multiplier
                else:
                    return native_max_hp_multiplier
            else:
                if hos_type != FRIENDLY_PLAYER_TYPE:
                    # Player and not default setting, so it is neccessary to
                    # adjust the hp multiplier. Extend it to 2.
                    power_health = 2 ** (self._entity.power_base * 0.25)
                    return (2 / power_health) * native_max_hp_multiplier
                else:
                    return native_max_hp_multiplier
    
    def get_modified_flags(self, relation, flags):
        """Gets the effective flags for a relation.
        
        Keyword arguments:
        relation -- Relation constant.
        flags -- The flags to modify.
        
        Returns:
        The modified flags.
        
        """
        if relation >= RELATION_HOSTILE_PLAYER:
            # hostile
            return flags | HOSTILE_FLAG
        else:
            # friendly
            return flags & ~HOSTILE_FLAG
    
    def _entity_removed(self, entity):
        """Removes an entity from the relation mapping when it has been
        destroyed.
        
        Keyword arguments:
        entity -- The removed CuBolt entity.
        
        """
        if entity._entity.entity_id in self.__relation_to:
            del self.__relation_to[entity._entity.entity_id]
    
    def send(self, players):
        """Sends this entitys data to the given players.
        
        Keyword arguments:
        players -- A list of players
        
        """
        if self.__initialized:
            e = self._entity
            f = e.flags
            eu = self.__entity_update_packet
            for player in players:
                pe = player.entity
                relation = pe.cubolt_entity.get_relation_to(self._entity)
                e.hostile_type = self.get_hostile_type_by_relation(relation)

                e.max_hp_multiplier = self.get_max_hp_multiplier_by_relation(
                    relation)
                e.mask |= self.get_mask_extension_by_relation(relation)
                e.flags = self.get_modified_flags(relation, e.flags)
            
                eu.set_entity(e, e.entity_id, e.mask)
                player.send_packet(eu)
        
            # Reset entity data to defaults, so all other scripts and server
            # algorithms are still working the intended way
            e.hostile_type = self._native_hostile_type
            e.max_hp_multiplier = self._native_max_hp_multiplier
            e.mask = 0
            e.flags = f
    
    # Following methods are injected into cuwo's default entity.
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
    def set_relation_to(self, entity, relation):
        """Sets the relation of this entity to another.
        
        Keyword arguments:
        entity -- cuwo entity to set the hostility to
        relation -- One of the relation constants
        
        """
        self.set_relation_to_id(entity.entity_id, relation)
        
    # injected
    def set_relation_to_id(self, entity_id, relation):
        """Sets the relation of this entity to another.
        
        Keyword arguments:
        entity_id -- ID of the entity to set the hostility to
        relation -- One of the relation constants.
        
        """
        own_id = self._entity.entity_id
        if entity_id != own_id:
            self.__relation_to[entity_id] = relation
            self._entity.mask |= MASK_HOSTILITY_SETTING
            self.__server.scripts.call('on_relation_changed',
                entity_from_id=own_id, entity_to_id=entity_id,
                relation=relation)
        
    # injected
    def set_relation_both(self, entity, relation):
        """Sets the relation of this entity to another and vice
        versa.
        
        Keyword arguments:
        entity -- cuwo entity to set the hostility to
        relation -- One of the relation constants
        
        """
        self.set_relation_to(entity, relation)
        entity.set_relation_to(self._entity, relation)
        
    # injected
    def set_relation_both_id(self, entity_id, relation):
        """Sets the relation of this entity to another and vice
        versa.
        
        Keyword arguments:
        entity_id -- ID of the entity to set the hostility to
        relation -- One of the relation constants.
        
        """
        entity = self._entity.world.entities[entity_id]
        self.set_relation_both(entity, relation)
    
    # injected
    def get_relation_to(self, entity):
        """Gets the relationn to the specified entity.
        
        Keyword arguments:
        entity -- Entity to get the relation to
        
        Returns:
        One of the relation constants
        
        """
        entity_id = entity.entity_id
        if not self.__initialized or entity_id == self._entity.entity_id:
            return RELATION_FRIENDLY_PLAYER
        elif entity_id in self.__relation_to:
            return self.__relation_to[entity_id]
        else:
            # determine from standards
            settings = NATIVE_SETTING_MAPPING[self._native_hostile_type]
            ce = entity.cubolt_entity
            return settings[ce._native_hostile_type]
        
    #injected
    def get_relation_to_id(self, entity_id):
        entity = self._entity.world[entity_id]
        return get_relation_to(entity)
    
    # injected
    def is_npc(self):
        """Checks whether this entity is an NPC entity.
        
        Returns:
        True if this is an NPC entity, otherwise False.
        
        """
        return self._native_hostile_type != FRIENDLY_PLAYER_TYPE

    # injected
    def is_player(self):
        """Checks whether this entity is a players entity.
        
        Returns:
        True if this is a players entity, otherwise False.
        
        """
        return self._native_hostile_type == FRIENDLY_PLAYER_TYPE
    
    # injected
    def teleport(self, location):
        """Teleports this entity to the desired location. It may take
        some time to set the actual pos of the entity in case this is a
        player's entity.
        
        Keyword arguments:
        location -- Location to port the entity to

        """
        if self.is_player():
            entity = self._entity
            update_packet = self.__server.update_packet
            player = self.__server.players[entity.entity_id]
            chunk = player.chunk
            pos = location
            
            def create_teleport_packet(pos, chunk_pos, user_id):
                packet = StaticEntityPacket()
                header = StaticEntityHeader()
                packet.header = header
                packet.chunk_x = chunk_pos[0]
                packet.chunk_y = chunk_pos[1]
                packet.entity_id = 0
                header.set_type('Bench')
                header.size = Vector3(0, 0, 0)
                header.closed = True
                header.orientation = ORIENT_SOUTH
                header.pos = pos
                header.time_offset = 0
                header.something8 = 0
                header.user_id = user_id
                return packet
            
            # Make the player sit down on an imaginary bench, this moves him
            packet = create_teleport_packet(pos, chunk.pos, entity.entity_id)
            
            # Send only to specific client
            self.__con_script.static_entities.append(packet)

            # Make him stand up again
            def send_reset_packet():
                if chunk.static_entities and id in chunk.static_entities:
                    chunk.static_entities[id].update()
                else:
                    packet = create_teleport_packet(pos, chunk.pos, 0)
                    # Send only to specific client
                    self.__con_script.static_entities.append(packet)

            cubolt_script = self.__server.scripts.cubolt
            cubolt_script.loop.call_later(0.1, send_reset_packet)
        else:
            self._entity.pos = location
            self._entity.mask |= POS_FLAG

    # injected
    def destroy(self):
        """Destroys this entity."""
        del self._entity.world.entities[self._entity.entity_id] 
        if not self._entity.static_id: 
            self._entity.world.entity_ids.put_back(self.entity_id) 

        for entity in self._entity.world.entities.values():
            entity.cubolt_entity._entity_removed(self)