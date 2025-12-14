"""
Faction warfare models for storing warzone-wide statistics and snapshots.
"""

from sqlalchemy import Column, Integer, Float, DateTime, String, Index
from sqlalchemy.sql import func

from ..database import Base


class FactionWarfareSnapshot(Base):
    """
    Model for storing warzone-wide faction warfare statistics snapshots.
    
    This table stores aggregated data for the entire warzone at specific points in time.
    """
    __tablename__ = "faction_warfare_snapshots"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Timestamp for this snapshot
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Minmatar statistics
    minmatar_systems_controlled = Column(Integer, default=0)
    minmatar_systems_contested = Column(Integer, default=0)
    minmatar_total_capture_percent = Column(Float, default=0.0)
    minmatar_total_advantage_percent = Column(Float, default=0.0)
    minmatar_kills_last_24h = Column(Integer, default=0)
    minmatar_losses_last_24h = Column(Integer, default=0)
    minmatar_kills_value_last_24h = Column(Float, default=0.0)
    minmatar_losses_value_last_24h = Column(Float, default=0.0)
    
    # Amarr statistics
    amarr_systems_controlled = Column(Integer, default=0)
    amarr_systems_contested = Column(Integer, default=0)
    amarr_total_capture_percent = Column(Float, default=0.0)
    amarr_total_advantage_percent = Column(Float, default=0.0)
    amarr_kills_last_24h = Column(Integer, default=0)
    amarr_losses_last_24h = Column(Integer, default=0)
    amarr_kills_value_last_24h = Column(Float, default=0.0)
    amarr_losses_value_last_24h = Column(Float, default=0.0)
    
    # Overall warzone statistics
    total_systems = Column(Integer, default=0)
    total_contested_systems = Column(Integer, default=0)
    total_kills_last_24h = Column(Integer, default=0)
    total_kill_value_last_24h = Column(Float, default=0.0)
    
    # Warzone control metrics
    minmatar_control_percentage = Column(Float, default=0.0)  # % of systems controlled
    amarr_control_percentage = Column(Float, default=0.0)     # % of systems controlled
    contested_percentage = Column(Float, default=0.0)         # % of systems contested
    
    # Activity metrics
    activity_index = Column(Float, default=0.0)  # Overall activity level (kills/hour)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('ix_fw_snapshots_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<FactionWarfareSnapshot(id={self.id}, timestamp={self.timestamp})>"
    
    @property
    def minmatar_efficiency(self) -> float:
        """Calculate Minmatar kill efficiency for the last 24 hours."""
        total_value = self.minmatar_kills_value_last_24h + self.minmatar_losses_value_last_24h
        if total_value > 0:
            return self.minmatar_kills_value_last_24h / total_value
        return 0.0
    
    @property
    def amarr_efficiency(self) -> float:
        """Calculate Amarr kill efficiency for the last 24 hours."""
        total_value = self.amarr_kills_value_last_24h + self.amarr_losses_value_last_24h
        if total_value > 0:
            return self.amarr_kills_value_last_24h / total_value
        return 0.0
