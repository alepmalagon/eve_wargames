from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Kill(Base):
    """Individual killmail record"""
    __tablename__ = "kills"
    
    # Primary identifiers from Zkillboard
    killmail_id = Column(Integer, primary_key=True)
    killmail_hash = Column(String(255), unique=True, nullable=False)
    
    # Context information
    system_id = Column(Integer, ForeignKey("systems.system_id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Value metrics
    total_value = Column(Float, default=0.0)  # ISK value
    points = Column(Integer, default=0)  # zkill points
    
    # Victim information
    victim_character_id = Column(Integer, ForeignKey("players.character_id"))
    victim_corporation_id = Column(Integer, ForeignKey("corporations.corporation_id"))
    victim_alliance_id = Column(Integer, ForeignKey("alliances.alliance_id"))
    victim_faction_id = Column(Integer)  # 500002 (Minmatar) or 500003 (Amarr)
    victim_ship_type_id = Column(Integer)
    
    # Attacker information (final blow)
    attacker_character_id = Column(Integer, ForeignKey("players.character_id"))
    attacker_corporation_id = Column(Integer, ForeignKey("corporations.corporation_id"))
    attacker_alliance_id = Column(Integer, ForeignKey("alliances.alliance_id"))
    attacker_faction_id = Column(Integer)  # 500002 (Minmatar) or 500003 (Amarr)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    system = relationship("System", backref="kills")
    victim_character = relationship("Player", foreign_keys=[victim_character_id], backref="victim_kills")
    victim_corporation = relationship("Corporation", foreign_keys=[victim_corporation_id], backref="victim_kills")
    victim_alliance = relationship("Alliance", foreign_keys=[victim_alliance_id], backref="victim_kills")
    attacker_character = relationship("Player", foreign_keys=[attacker_character_id], backref="attacker_kills")
    attacker_corporation = relationship("Corporation", foreign_keys=[attacker_corporation_id], backref="attacker_kills")
    attacker_alliance = relationship("Alliance", foreign_keys=[attacker_alliance_id], backref="attacker_kills")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_kills_system_timestamp', 'system_id', 'timestamp'),
        Index('idx_kills_victim_faction', 'victim_faction_id', 'timestamp'),
        Index('idx_kills_attacker_faction', 'attacker_faction_id', 'timestamp'),
        Index('idx_kills_timestamp_desc', 'timestamp', postgresql_using='btree'),
    )


class Player(Base):
    """EVE Online character/player"""
    __tablename__ = "players"
    
    character_id = Column(Integer, primary_key=True)
    character_name = Column(String(255), unique=True, nullable=False)
    corporation_id = Column(Integer, ForeignKey("corporations.corporation_id"))
    alliance_id = Column(Integer, ForeignKey("alliances.alliance_id"))
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    corporation = relationship("Corporation", backref="members")
    alliance = relationship("Alliance", backref="members")


class Corporation(Base):
    """EVE Online corporation"""
    __tablename__ = "corporations"
    
    corporation_id = Column(Integer, primary_key=True)
    corporation_name = Column(String(255), unique=True, nullable=False)
    alliance_id = Column(Integer, ForeignKey("alliances.alliance_id"))
    ticker = Column(String(10))
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    alliance = relationship("Alliance", backref="corporations")


class Alliance(Base):
    """EVE Online alliance"""
    __tablename__ = "alliances"
    
    alliance_id = Column(Integer, primary_key=True)
    alliance_name = Column(String(255), unique=True, nullable=False)
    ticker = Column(String(10))
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class SystemKillStats(Base):
    """Aggregated kill statistics per system"""
    __tablename__ = "system_kill_stats"
    
    id = Column(Integer, primary_key=True)
    system_id = Column(Integer, ForeignKey("systems.system_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.now())
    
    # Time window for these stats (in hours)
    time_window_hours = Column(Integer, default=24)
    
    # Overall statistics
    total_kills = Column(Integer, default=0)
    total_isk_value = Column(Float, default=0.0)
    
    # Faction-specific statistics
    minmatar_kills = Column(Integer, default=0)
    minmatar_losses = Column(Integer, default=0)
    minmatar_isk_killed = Column(Float, default=0.0)
    minmatar_isk_lost = Column(Float, default=0.0)
    
    amarr_kills = Column(Integer, default=0)
    amarr_losses = Column(Integer, default=0)
    amarr_isk_killed = Column(Float, default=0.0)
    amarr_isk_lost = Column(Float, default=0.0)
    
    # Activity metrics
    unique_players = Column(Integer, default=0)
    unique_corporations = Column(Integer, default=0)
    unique_alliances = Column(Integer, default=0)
    
    # Relationships
    system = relationship("System", backref="kill_stats")
    
    # Indexes
    __table_args__ = (
        Index('idx_system_kill_stats_system_time', 'system_id', 'timestamp'),
        Index('idx_system_kill_stats_time_window', 'system_id', 'time_window_hours', 'timestamp'),
    )


class PlayerKillStats(Base):
    """Aggregated kill statistics per player per system"""
    __tablename__ = "player_kill_stats"
    
    id = Column(Integer, primary_key=True)
    system_id = Column(Integer, ForeignKey("systems.system_id"), nullable=False)
    character_id = Column(Integer, ForeignKey("players.character_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.now())
    time_window_hours = Column(Integer, default=24)
    
    # Statistics
    kills_count = Column(Integer, default=0)
    losses_count = Column(Integer, default=0)
    isk_killed = Column(Float, default=0.0)
    isk_lost = Column(Float, default=0.0)
    
    # Relationships
    system = relationship("System")
    player = relationship("Player")
    
    # Indexes
    __table_args__ = (
        Index('idx_player_kill_stats_system_player', 'system_id', 'character_id', 'timestamp'),
        Index('idx_player_kill_stats_kills_desc', 'system_id', 'kills_count', postgresql_using='btree'),
    )


class CorporationKillStats(Base):
    """Aggregated kill statistics per corporation per system"""
    __tablename__ = "corporation_kill_stats"
    
    id = Column(Integer, primary_key=True)
    system_id = Column(Integer, ForeignKey("systems.system_id"), nullable=False)
    corporation_id = Column(Integer, ForeignKey("corporations.corporation_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.now())
    time_window_hours = Column(Integer, default=24)
    
    # Statistics
    kills_count = Column(Integer, default=0)
    losses_count = Column(Integer, default=0)
    isk_killed = Column(Float, default=0.0)
    isk_lost = Column(Float, default=0.0)
    unique_players = Column(Integer, default=0)
    
    # Relationships
    system = relationship("System")
    corporation = relationship("Corporation")
    
    # Indexes
    __table_args__ = (
        Index('idx_corp_kill_stats_system_corp', 'system_id', 'corporation_id', 'timestamp'),
        Index('idx_corp_kill_stats_kills_desc', 'system_id', 'kills_count', postgresql_using='btree'),
    )


class AllianceKillStats(Base):
    """Aggregated kill statistics per alliance per system"""
    __tablename__ = "alliance_kill_stats"
    
    id = Column(Integer, primary_key=True)
    system_id = Column(Integer, ForeignKey("systems.system_id"), nullable=False)
    alliance_id = Column(Integer, ForeignKey("alliances.alliance_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.now())
    time_window_hours = Column(Integer, default=24)
    
    # Statistics
    kills_count = Column(Integer, default=0)
    losses_count = Column(Integer, default=0)
    isk_killed = Column(Float, default=0.0)
    isk_lost = Column(Float, default=0.0)
    unique_players = Column(Integer, default=0)
    unique_corporations = Column(Integer, default=0)
    
    # Relationships
    system = relationship("System")
    alliance = relationship("Alliance")
    
    # Indexes
    __table_args__ = (
        Index('idx_alliance_kill_stats_system_alliance', 'system_id', 'alliance_id', 'timestamp'),
        Index('idx_alliance_kill_stats_kills_desc', 'system_id', 'kills_count', postgresql_using='btree'),
    )
