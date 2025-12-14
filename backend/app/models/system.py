"""
System models for storing EVE Online system and faction warfare data.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base


class System(Base):
    """
    Model for storing EVE Online system information.
    """
    __tablename__ = "systems"
    
    # Primary key
    system_id = Column(Integer, primary_key=True, index=True)
    
    # Basic system information
    name = Column(String(255), nullable=False, index=True)
    security_status = Column(Float, nullable=False)
    
    # Current faction warfare status
    controlling_faction_id = Column(Integer, ForeignKey("factions.faction_id"), nullable=True)
    contested = Column(Integer, default=0)  # 0 = stable, 1 = contested
    
    # Current control percentages (latest snapshot)
    capture_percent = Column(Float, default=0.0)
    advantage_percent = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    controlling_faction = relationship("Faction", back_populates="systems")
    snapshots = relationship("SystemSnapshot", back_populates="system", cascade="all, delete-orphan")
    kills = relationship("Kill", back_populates="system")
    
    def __repr__(self):
        return f"<System(system_id={self.system_id}, name='{self.name}')>"


class SystemSnapshot(Base):
    """
    Model for storing historical system control data.
    
    This table stores time-series data for tracking system control changes over time.
    """
    __tablename__ = "system_snapshots"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    system_id = Column(Integer, ForeignKey("systems.system_id"), nullable=False)
    controlling_faction_id = Column(Integer, ForeignKey("factions.faction_id"), nullable=True)
    
    # Faction warfare data
    contested = Column(Integer, default=0)  # 0 = stable, 1 = contested
    capture_percent = Column(Float, default=0.0)
    advantage_percent = Column(Float, default=0.0)
    
    # Timestamp for this snapshot
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    system = relationship("System", back_populates="snapshots")
    controlling_faction = relationship("Faction", back_populates="system_snapshots")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('ix_system_snapshots_system_timestamp', 'system_id', 'timestamp'),
        Index('ix_system_snapshots_faction_timestamp', 'controlling_faction_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<SystemSnapshot(system_id={self.system_id}, timestamp={self.timestamp})>"
