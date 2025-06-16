"""
Property model for rental properties
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import uuid


class PropertyModel(BaseModel):
    """
    Simplified property model based on real rental data
    
    Represents rental properties from real estate platforms like Rightmove
    """
    
    # Core identification (from real data)
    property_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Basic property details (from real data)
    bedrooms: int = 1
    bathrooms: int = 1
    display_address: str = "Unknown Address"
    
    # Pricing information (from real data structure)
    price: Dict[str, Any] = Field(default_factory=lambda: {
        'amount': 2000,
        'frequency': 'monthly',
        'currencyCode': 'GBP'
    })
    
    # Location data (from real data)
    location: Dict[str, float] = Field(default_factory=lambda: {
        'latitude': 51.5074,
        'longitude': -0.1278
    })
    
    # Property type (from real data)
    property_sub_type: str = "Apartment"  # Apartment, House, Flat, Terraced, etc.
    property_type_full_description: Optional[str] = None
    
    # Property description (from real data)
    summary: str = "No description available"
    
    # Media content (from real data)
    property_images: Optional[Dict[str, Any]] = None
    
    # Landlord/agent information (from real data)
    customer: Optional[Dict[str, Any]] = None
    formatted_branch_name: Optional[str] = None
    landlord_id: Optional[str] = None  # For linking to landlord data
    
    def model_post_init(self, __context) -> None:
        """Post-initialization validation and processing"""
        # Ensure price has required fields
        if 'amount' not in self.price:
            self.price['amount'] = 2000
        if 'frequency' not in self.price:
            self.price['frequency'] = 'monthly'
        if 'currencyCode' not in self.price:
            self.price['currencyCode'] = 'GBP'
            
        # Ensure location has required coordinates
        if 'latitude' not in self.location:
            self.location['latitude'] = 51.5074
        if 'longitude' not in self.location:
            self.location['longitude'] = -0.1278
    
    @property
    def monthly_rent(self) -> float:
        """Get monthly rent amount"""
        amount = self.price.get('amount', 0)
        frequency = self.price.get('frequency', 'monthly')
        
        if frequency == 'weekly':
            return amount * 52 / 12  # Convert weekly to monthly
        elif frequency == 'yearly':
            return amount / 12  # Convert yearly to monthly
        else:  # monthly or default
            return amount
    
    @property
    def coordinates(self) -> tuple:
        """Get location coordinates as tuple"""
        return (self.location.get('latitude', 51.5074), 
                self.location.get('longitude', -0.1278))
    
    def get_main_image(self) -> Optional[str]:
        """Get main property image URL"""
        if self.property_images and isinstance(self.property_images, dict):
            return self.property_images.get('mainImageSrc')
        return None
    
    def get_all_images(self) -> List[str]:
        """Get all property image URLs"""
        images = []
        if self.property_images and isinstance(self.property_images, dict):
            # Add main image
            main_img = self.property_images.get('mainImageSrc')
            if main_img:
                images.append(main_img)
            
            # Add other images
            if 'images' in self.property_images and isinstance(self.property_images['images'], list):
                for img in self.property_images['images']:
                    if isinstance(img, dict) and 'srcUrl' in img:
                        images.append(img['srcUrl'])
        return images
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization (backward compatibility)"""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PropertyModel':
        """Create PropertyModel from dictionary (backward compatibility)"""
        return cls.model_validate(data)
    
    @classmethod
    def from_rightmove_data(cls, rightmove_data: Dict[str, Any]) -> 'PropertyModel':
        """Create PropertyModel from Rightmove API data"""
        return cls(
            property_id=str(rightmove_data.get('property_id', uuid.uuid4())),
            bedrooms=rightmove_data.get('bedrooms', 1),
            bathrooms=rightmove_data.get('bathrooms', 1),
            display_address=rightmove_data.get('display_address', 'Unknown Address'),
            price=rightmove_data.get('price', {'amount': 2000, 'frequency': 'monthly', 'currencyCode': 'GBP'}),
            location=rightmove_data.get('location', {'latitude': 51.5074, 'longitude': -0.1278}),
            property_sub_type=rightmove_data.get('property_sub_type', 'Apartment'),
            property_type_full_description=rightmove_data.get('property_type_full_description'),
            summary=rightmove_data.get('summary', 'No description available'),
            property_images=rightmove_data.get('property_images'),
            customer=rightmove_data.get('customer'),
            formatted_branch_name=rightmove_data.get('formatted_branch_name')
        )
    
    def __str__(self) -> str:
        """String representation"""
        return f"Property({self.property_id} - {self.bedrooms}bed, {self.display_address})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"PropertyModel(id={self.property_id}, bedrooms={self.bedrooms}, "
                f"bathrooms={self.bathrooms}, price={self.monthly_rent}, "
                f"type='{self.property_sub_type}', address='{self.display_address}')")