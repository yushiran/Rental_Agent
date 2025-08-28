"""
Landlord model for property owners
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from .property_model import PropertyModel


class LandlordRentalStatus(BaseModel):
    """Landlord rental statistics"""
    total_properties: int = 0
    rented_properties: int = 0
    available_properties: int = 0
    total_rental_income: float = 0.0
    average_rental_price: float = 0.0
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())

class LandlordModel(BaseModel):
    """
    Simplified landlord model based on real rental data
    
    Represents property agents/landlords from rental platforms
    """
    
    # Core identification (from real data: branchId)
    landlord_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Basic information (from real data)
    name: str = "Unknown Landlord"  # branchDisplayName or brandTradingName
    phone: Optional[str] = None  # contactTelephone
    branch_name: Optional[str] = None  # branchName (location)
    
    # Properties owned/managed
    properties: List[PropertyModel] = Field(default_factory=list)
    
    # Simplified preferences (commonly found in real rental requirements)
    preferences: Dict[str, Any] = Field(default_factory=lambda: {
        'pet_friendly': False,
        'smoking_allowed': False,
        'deposit_weeks': 4  # Number of weeks rent as deposit
    })

    rental_stats: LandlordRentalStatus = Field(default_factory=LandlordRentalStatus)

    # Timestamps
    date_registered: datetime = Field(default_factory=datetime.now)
    
    def model_post_init(self, __context):
        """Post-initialization validation"""
        # Ensure preferences has required fields
        default_preferences = {
            'pet_friendly': False,
            'smoking_allowed': False,
            'deposit_weeks': 4
        }
        for key, value in default_preferences.items():
            if key not in self.preferences:
                self.preferences[key] = value
    
    @property
    def total_properties(self) -> int:
        """Get total number of properties"""
        return len(self.properties)
    
    @property
    def available_properties(self) -> List[PropertyModel]:
        """Get list of all properties (simplified - no availability tracking)"""
        return self.properties
    
    @property
    def total_available_properties(self) -> int:
        """Get count of available properties"""
        return len(self.available_properties)
    
    @property
    def average_rent(self) -> float:
        """Calculate average monthly rent across all properties"""
        if not self.properties:
            return 0.0
        total_rent = sum(prop.monthly_rent for prop in self.properties)
        return total_rent / len(self.properties)
    
    def add_property(self, property_model: PropertyModel) -> None:
        """Add a property to the landlord's portfolio"""
        if property_model not in self.properties:
            self.properties.append(property_model)
    
    def remove_property(self, property_id: str) -> bool:
        """Remove a property from the portfolio"""
        for i, prop in enumerate(self.properties):
            if prop.property_id == property_id:
                self.properties.pop(i)
                return True
        return False
    
    def get_property(self, property_id: str) -> Optional[PropertyModel]:
        """Get a specific property by ID"""
        for prop in self.properties:
            if prop.property_id == property_id:
                return prop
        return None
    
    def get_properties_by_criteria(self, 
                                 min_bedrooms: Optional[int] = None,
                                 max_bedrooms: Optional[int] = None,
                                 min_price: Optional[float] = None,
                                 max_price: Optional[float] = None,
                                 property_type: Optional[str] = None) -> List[PropertyModel]:
        """Filter properties by criteria"""
        filtered_properties = self.properties
        
        if min_bedrooms is not None:
            filtered_properties = [prop for prop in filtered_properties if prop.bedrooms >= min_bedrooms]
        
        if max_bedrooms is not None:
            filtered_properties = [prop for prop in filtered_properties if prop.bedrooms <= max_bedrooms]
        
        if min_price is not None:
            filtered_properties = [prop for prop in filtered_properties if prop.monthly_rent >= min_price]
        
        if max_price is not None:
            filtered_properties = [prop for prop in filtered_properties if prop.monthly_rent <= max_price]
        
        if property_type is not None:
            filtered_properties = [prop for prop in filtered_properties if prop.property_sub_type.lower() == property_type.lower()]
        
        return filtered_properties
    
    def update_preferences(self, preference_updates: Dict[str, Any]) -> None:
        """Update landlord preferences"""
        self.preferences.update(preference_updates)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization (backward compatibility)"""
        result = self.model_dump()
        # Convert datetime to ISO format for compatibility
        if 'date_registered' in result and isinstance(result['date_registered'], datetime):
            result['date_registered'] = result['date_registered'].isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LandlordModel':
        """Create LandlordModel from dictionary (backward compatibility)"""
        # Handle datetime fields
        if 'date_registered' in data and isinstance(data['date_registered'], str):
            data['date_registered'] = datetime.fromisoformat(data['date_registered'])
        
        # Convert property dictionaries to PropertyModel objects
        if 'properties' in data and isinstance(data['properties'], list):
            data['properties'] = [
                PropertyModel.from_dict(prop_data) if isinstance(prop_data, dict) else prop_data
                for prop_data in data['properties']
            ]
        
        return cls.model_validate(data)
    
    def __str__(self) -> str:
        """String representation"""
        return f"Landlord({self.name} - {self.total_properties} properties)"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"LandlordModel(id={self.landlord_id}, name='{self.name}', "
                f"properties={self.total_properties})")