"""
Tenant model for rental property seekers
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import uuid
import math
from datetime import datetime

class RentalStatus(BaseModel):
    """Tenant rental status"""
    is_rented: bool = False
    property_id: Optional[str] = None
    landlord_id: Optional[str] = None
    rental_price: Optional[float] = None
    rental_start_date: Optional[str] = None
    contract_duration_months: Optional[int] = None
    negotiation_session_id: Optional[str] = None
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())


class TenantModel(BaseModel):
    """
    Simplified tenant model for rental property matching
    
    Contains only essential information for property search and matching
    """
    
    # Core identification
    tenant_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Basic information
    name: str = "Unknown Tenant"
    email: Optional[str] = None
    phone: Optional[str] = None
    
    # Essential financial info
    annual_income: float = 0.0
    has_guarantor: bool = False
    
    # Core rental preferences
    max_budget: float = 2000.0  # Monthly budget
    min_bedrooms: int = 1
    max_bedrooms: int = 3
    preferred_locations: List[Dict[str, float]] = Field(default_factory=list)  # List of preferred coordinates [{"latitude": lat, "longitude": lon}]
    
    # Personal circumstances (simplified)
    is_student: bool = False
    has_pets: bool = False
    is_smoker: bool = False
    num_occupants: int = 1  # Including the tenant

    rental_status: RentalStatus = Field(default_factory=RentalStatus)
    
    @property
    def monthly_income(self) -> float:
        """Get monthly income"""
        return self.annual_income / 12
    
    def can_afford_property(self, monthly_rent: float, income_ratio: float = 3.0) -> bool:
        """Check if tenant can afford a property based on income ratio"""
        return self.monthly_income >= (monthly_rent * income_ratio)
    
    def calculate_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of Earth in kilometers
        r = 6371
        return c * r
    
    def get_closest_preferred_location_distance(self, property_lat: float, property_lon: float) -> float:
        """Get distance to closest preferred location"""
        if not self.preferred_locations:
            return float('inf')
        
        min_distance = float('inf')
        for location in self.preferred_locations:
            distance = self.calculate_distance_km(
                property_lat, property_lon,
                location['latitude'], location['longitude']
            )
            min_distance = min(min_distance, distance)
        
        return min_distance
    
    def matches_property_criteria(self, property_model) -> Dict[str, Any]:
        """Check how well the property matches tenant's criteria"""
        from .property_model import PropertyModel
        
        if not isinstance(property_model, PropertyModel):
            return {'matches': False, 'score': 0.0, 'reasons': ['Invalid property']}
        
        score = 0.0
        max_score = 100.0
        reasons = []
        
        # Budget check (30% weight)
        if property_model.monthly_rent <= self.max_budget:
            score += 30
            reasons.append('Within budget')
        else:
            reasons.append(f'Over budget by £{property_model.monthly_rent - self.max_budget:.2f}')
        
        # Bedroom count (30% weight)
        if self.min_bedrooms <= property_model.bedrooms <= self.max_bedrooms:
            score += 30
            reasons.append('Bedroom count matches')
        else:
            reasons.append('Bedroom count doesn\'t match preferences')
        
        # Location preference (30% weight)
        if self.preferred_locations:
            property_lat, property_lon = property_model.coordinates
            closest_distance = self.get_closest_preferred_location_distance(property_lat, property_lon)
            
            if closest_distance <= 2.0:  # Within 2km
                score += 30
                reasons.append(f'Close to preferred location ({closest_distance:.1f}km)')
            elif closest_distance <= 5.0:  # Within 5km
                score += 20
                reasons.append(f'Near preferred location ({closest_distance:.1f}km)')
            elif closest_distance <= 10.0:  # Within 10km
                score += 10
                reasons.append(f'Moderately close to preferred location ({closest_distance:.1f}km)')
            else:
                reasons.append(f'Far from preferred locations ({closest_distance:.1f}km)')
        else:
            score += 15  # Give some points if no location preference
            reasons.append('No location preference specified')
        
        # Property type preference (10% weight)
        if hasattr(property_model, 'property_sub_type'):
            score += 10  # Always give points for having property type
            reasons.append(f'Property type: {property_model.property_sub_type}')
        
        matches = score >= 60  # 60% threshold for a match
        
        return {
            'matches': matches,
            'score': round(score, 2),
            'reasons': reasons,
            'affordability': self.can_afford_property(property_model.monthly_rent),
            'distance_to_preferred_km': self.get_closest_preferred_location_distance(*property_model.coordinates) if self.preferred_locations else None
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization (backward compatibility)"""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TenantModel':
        """Create TenantModel from dictionary (backward compatibility)"""
        return cls.model_validate(data)
    
    def __str__(self) -> str:
        """String representation"""
        return f"Tenant({self.name} - Budget: £{self.max_budget}/month)"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"TenantModel(id={self.tenant_id}, name='{self.name}', "
                f"budget={self.max_budget}, bedrooms={self.min_bedrooms}-{self.max_bedrooms})")
