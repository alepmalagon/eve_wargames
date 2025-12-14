"""
Kill models for storing EVE Online killmail and kill statistics data.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, BigInteger, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base


class Kill(Base):
    """
    Model for storing individual killmail data.
    """
    __tablename__ = "kills"
    
    # Primary key
    killmail_id = Column(BigInteger, primary_key=True, index=True)
    
    # Location information
    system_id = Column(Integer, ForeignKey("systems.system_id"), nullable=False)
    
    # Victim information
    victim_character_id = Column(Integer, nullable=True)
    victim_corporation_id = Column(Integer, nullable=True)
    victim_alliance_id = Column(Integer, nullable=True)
    victim_faction_id = Column(Integer, ForeignKey("factions.faction_id"), nullable=True)
    victim_ship_type_id = Column(Integer, nullable=False)
    
    # Final blow attacker information
    final_blow_character_id = Column(Integer, nullable=True)
    final_blow_corporation_id = Column(Integer, nullable=True)
    final_blow_alliance_id = Column(Integer, nullable=True)
    final_blow_faction_id = Column(Integer, ForeignKey("factions.faction_id"), nullable=True)
    final_blow_ship_type_id = Column(Integer, nullable=True)
    
    # Kill details
    kill_time = Column(DateTime(timezone=True), nullable=False, index=True)
    total_value = Column(Float, default=0.0)  # ISK value of the kill
    attacker_count = Column(Integer, default=1)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    system = relationship("System", back_populates="kills")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('ix_kills_system_time', 'system_id', 'kill_time'),
        Index('ix_kills_victim_faction_time', 'victim_faction_id', 'kill_time'),
        Index('ix_kills_attacker_faction_time', 'final_blow_faction_id', 'kill_time'),
        Index('ix_kills_victim_corp_time', 'victim_corporation_id', 'kill_time'),
        Index('ix_kills_attacker_corp_time', 'final_blow_corporation_id', 'kill_time'),
    )
    
    def __repr__(self):
        return f"<Kill(killmail_id={self.killmail_id}, system_id={self.system_id})>"


class KillStatistic(Base):
    """
    Model for storing aggregated kill statistics.
    
    This table stores pre-calculated statistics for efficient querying of kill data.
    """
    __tablename__ = "kill_statistics"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Aggregation dimensions
    system_id = Column(Integer, ForeignKey("systems.system_id"), nullable=True)
    faction_id = Column(Integer, ForeignKey("factions.faction_id"), nullable=True)
    corporation_id = Column(Integer, nullable=True)
    alliance_id = Column(Integer, nullable=True)
    
    # Time period for this statistic
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(50), nullable=False)  # 'hour', 'day', 'week', 'month'
    
    # Kill statistics
    kills_count = Column(Integer, default=0)
    losses_count = Column(Integer, default=0)
    kills_value = Column(Float, default=0.0)  # Total ISK value of kills
    losses_value = Column(Float, default=0.0)  # Total ISK value of losses
    
    # Efficiency metrics
    efficiency = Column(Float, default=0.0)  # kills_value / (kills_value + losses_value)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('ix_kill_stats_system_period', 'system_id', 'period_start', 'period_end'),
        Index('ix_kill_stats_faction_period', 'faction_id', 'period_start', 'period_end'),
        Index('ix_kill_stats_corp_period', 'corporation_id', 'period_start', 'period_end'),
        Index('ix_kill_stats_alliance_period', 'alliance_id', 'period_start', 'period_end'),
        Index('ix_kill_stats_period_type', 'period_type', 'period_start'),
    )
    
    def __repr__(self):
        return f"<KillStatistic(id={self.id}, period={self.period_start}-{self.period_end})>"
