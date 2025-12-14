"""
Faction model for storing EVE Online faction information.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base


class Faction(Base):
    """
    Model for storing EVE Online faction information.
    """
    __tablename__ = "factions"
    
    # Primary key
    faction_id = Column(Integer, primary_key=True, index=True)
    
    # Basic faction information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    
    # Faction warfare specific
    is_militia = Column(Boolean, default=False)
    militia_corporation_id = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    systems = relationship("System", back_populates="controlling_faction")
    system_snapshots = relationship("SystemSnapshot", back_populates="controlling_faction")
    
    def __repr__(self):
        return f"<Faction(faction_id={self.faction_id}, name='{self.name}')>"
