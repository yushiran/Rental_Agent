"""
Utility functions for multi-party rental negotiations
"""
from typing import List, Optional

from app.mongo import MongoClientWrapper
from app.agents.models import LandlordModel, TenantModel, PropertyModel
from .models import ParticipantRole


class ParticipantUtils:
    """Utility class for managing participants"""
    
    def __init__(self):
        self.landlords_db = MongoClientWrapper(
            model=LandlordModel,
            collection_name="landlords"
        )
        self.tenants_db = MongoClientWrapper(
            model=TenantModel,
            collection_name="tenants"
        )
        self.properties_db = MongoClientWrapper(
            model=PropertyModel,
            collection_name="properties"
        )
    
    async def find_suitable_tenants(
        self, 
        property_id: str, 
        max_budget: float,
        min_bedrooms: int,
        max_bedrooms: int,
        limit: int = 5
    ) -> List[TenantModel]:
        """Find tenants suitable for a property"""
        try:
            query = {
                "max_budget": {"$gte": max_budget * 0.8},  # Allow 20% flexibility
                "min_bedrooms": {"$lte": max_bedrooms},
                "max_bedrooms": {"$gte": min_bedrooms}
            }
            
            results = self.tenants_db.fetch_documents(limit=limit, query=query)
            return [TenantModel.from_dict(result.model_dump()) for result in results]
            
        except Exception as e:
            print(f"Error finding suitable tenants: {str(e)}")
            return []
    
    async def find_competing_properties(
        self, 
        target_property_id: str,
        price_range: float = 200.0,
        limit: int = 3
    ) -> List[PropertyModel]:
        """Find competing properties for market analysis"""
        try:
            # Get target property details
            target_results = self.properties_db.fetch_documents(
                limit=1, 
                query={"property_id": target_property_id}
            )
            if not target_results:
                return []
            
            target_prop = target_results[0]
            target_rent = getattr(target_prop, "monthly_rent", 0)
            target_bedrooms = getattr(target_prop, "bedrooms", 1)
            
            # Find similar properties
            query = {
                "property_id": {"$ne": target_property_id},
                "monthly_rent": {
                    "$gte": target_rent - price_range,
                    "$lte": target_rent + price_range
                },
                "bedrooms": target_bedrooms
            }
            
            results = self.properties_db.fetch_documents(limit=limit, query=query)
            return [PropertyModel.from_dict(result.model_dump()) for result in results]
            
        except Exception as e:
            print(f"Error finding competing properties: {str(e)}")
            return []
    

