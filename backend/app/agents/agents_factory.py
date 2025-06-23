"""
Data initialization script - Create Landlords and Tenants from real JSON data
"""

import json
import random
from typing import List, Dict, Any

from loguru import logger
from faker import Faker

from app.mongo import MongoClientWrapper
from app.agents.models import PropertyModel, LandlordModel, TenantModel
from app.config import config


class AgentDataInitializer:
    """Agent Data Initializer"""
    
    def __init__(self):
        # Faker instance for generating UK-based fake data
        self.fake: Faker = Faker(['en_GB'])
        
        # MongoDB client wrapper for landlord collection operations
        self.landlord_client= MongoClientWrapper(
            model=LandlordModel, 
            collection_name="landlords"
        )
        
        # MongoDB client wrapper for tenant collection operations  
        self.tenant_client = MongoClientWrapper(
            model=TenantModel, 
            collection_name="tenants"
        )
        
        # MongoDB client wrapper for property collection operations
        self.property_client = MongoClientWrapper(
            model=PropertyModel, 
            collection_name="properties"
        )
        
    def load_rightmove_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Load Rightmove data"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Successfully loaded {len(data)} property records")
            
            # Deduplicate properties by property ID
            unique_properties = {}
            for prop in data:
                # Using property ID as the unique identifier
                # If no proper ID exists, create a composite key from address and price
                prop_id = prop.get('id') or prop.get('propertyId') or f"{prop.get('displayAddress', '')}-{prop.get('price', '')}"
                unique_properties[prop_id] = prop
            
            deduplicated_data = list(unique_properties.values())
            logger.info(f"After deduplication: {len(deduplicated_data)} unique property records")
            return deduplicated_data
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return []
    
    def clean_property_data(self, raw_property: Dict[str, Any]) -> PropertyModel:
        """Clean and transform property data"""
        return PropertyModel.from_rightmove_data(raw_property)
    
    def _create_landlord(self, properties: List[PropertyModel]) -> LandlordModel:
        """Create a landlord with associated properties"""
        # Use property data to generate realistic landlord info
        first_property = properties[0] if properties else None
        
        # Generate landlord name from branch or agent data
        name = self.fake.company()
        phone = self.fake.phone_number()
        branch_name = self.fake.city()
        
        # Use actual data from properties if available
        if first_property and first_property.formatted_branch_name:
            branch_name = first_property.formatted_branch_name
        if first_property and first_property.customer:
            customer_data = first_property.customer
            if isinstance(customer_data, dict) and 'brandTradingName' in customer_data:
                name = customer_data['brandTradingName']
        
        # Generate preferences
        preferences = {
            'pet_friendly': random.choice([True, False]),
            'smoking_allowed': random.choice([True, False]),
            'deposit_weeks': random.choice([4, 5, 6])
        }
        
        return LandlordModel(
            name=name,
            phone=phone,
            branch_name=branch_name,
            properties=properties.copy(),
            preferences=preferences
        )
    
    def create_landlords_from_properties(self, properties: List[PropertyModel]) -> List[LandlordModel]:
        """Create landlords based on property data"""
        landlords = []
        
        # Group properties for different landlords
        properties_per_landlord = random.randint(1, 5)
        current_properties = []
        
        for i, property_data in enumerate(properties):
            current_properties.append(property_data)
            
            # Create a landlord after accumulating certain number of properties or reaching the last one
            if len(current_properties) >= properties_per_landlord or i == len(properties) - 1:
                landlord = self._create_landlord(current_properties)
                landlords.append(landlord)
                current_properties = []
                properties_per_landlord = random.randint(1, 5)
        
        logger.info(f"Created {len(landlords)} landlords")
        return landlords
    
    def create_random_tenants(self, count: int = 200) -> List[TenantModel]:
        """Create random tenants"""
        tenants = []
        
        # London area coordinates (latitude, longitude) with area names for reference
        london_coordinates = [
            {"latitude": 51.5074, "longitude": -0.1278, "name": "Central London"},
            {"latitude": 51.5393, "longitude": -0.1435, "name": "Camden"},
            {"latitude": 51.5465, "longitude": -0.1033, "name": "Islington"},
            {"latitude": 51.5450, "longitude": -0.0553, "name": "Hackney"},
            {"latitude": 51.5118, "longitude": -0.0425, "name": "Tower Hamlets"},
            {"latitude": 51.4934, "longitude": 0.0098, "name": "Greenwich"},
            {"latitude": 51.4417, "longitude": -0.0143, "name": "Lewisham"},
            {"latitude": 51.5035, "longitude": -0.0954, "name": "Southwark"},
            {"latitude": 51.4975, "longitude": -0.1113, "name": "Lambeth"},
            {"latitude": 51.4571, "longitude": -0.1787, "name": "Wandsworth"},
            {"latitude": 51.4927, "longitude": -0.2339, "name": "Hammersmith"},
            {"latitude": 51.4994, "longitude": -0.1746, "name": "Kensington"},
            {"latitude": 51.4975, "longitude": -0.1357, "name": "Westminster"},
            {"latitude": 51.5054, "longitude": -0.0236, "name": "Canary Wharf"},
            {"latitude": 51.5434, "longitude": -0.0103, "name": "Stratford"},
            {"latitude": 51.4959, "longitude": -0.0637, "name": "Bermondsey"},
            {"latitude": 51.4613, "longitude": -0.1157, "name": "Brixton"},
            {"latitude": 51.4654, "longitude": -0.1390, "name": "Clapham"}
        ]
        
        for _ in range(count):
            # Generate budget (based on London rental market)
            budget_ranges = [
                (600, 800),  # Students/Young professionals
                (800, 1000),  # Mid-level professionals
                (1000, 1500),  # Senior professionals
                (1500, 3000)  # Executive level
            ]
            budget_range = random.choice(budget_ranges)
            max_budget = random.randint(*budget_range)
            
            # Generate annual income (3-5 times monthly budget)
            annual_income = max_budget * 12 * random.uniform(3.0, 5.0)
            
            # Preferred locations (1-3 coordinates)
            num_preferred = random.randint(1, 3)
            preferred_locations = []
            for coord in random.sample(london_coordinates, num_preferred):
                # Add some random variation to coordinates (within ~1km radius)
                lat_variation = random.uniform(-0.01, 0.01)  # ~1km variation
                lon_variation = random.uniform(-0.01, 0.01)
                preferred_locations.append({
                    "latitude": coord["latitude"] + lat_variation,
                    "longitude": coord["longitude"] + lon_variation
                })
            
            is_student = random.choice([True, False])
            has_pets = random.choice([True, False])
            is_smoker = random.choice([True, False])
            has_guarantor = random.choice([True, False])
            
            # Bedroom preferences
            min_bedrooms = random.randint(1, 2)
            max_bedrooms = random.randint(min_bedrooms, min_bedrooms + 2)
            
            tenant = TenantModel(
                name=self.fake.name(),
                email=self.fake.email(),
                phone=self.fake.phone_number(),
                annual_income=annual_income,
                has_guarantor=has_guarantor,
                max_budget=max_budget,
                min_bedrooms=min_bedrooms,
                max_bedrooms=max_bedrooms,
                preferred_locations=preferred_locations,
                is_student=is_student,
                has_pets=has_pets,
                is_smoker=is_smoker,
                num_occupants=random.randint(1, 3)
            )
            
            tenants.append(tenant)
        
        logger.info(f"Created {len(tenants)} tenants")
        return tenants
    
    def save_to_mongodb(self, landlords: List[LandlordModel], tenants: List[TenantModel]):
        """Save data to MongoDB"""
        try:
            # Clear existing data
            self.landlord_client.collection.delete_many({})
            self.tenant_client.collection.delete_many({})
            self.property_client.collection.delete_many({})
            
            # Save landlord data
            landlord_dicts = []
            property_dicts = []
            
            for landlord in landlords:
                landlord_dict = landlord.to_dict()
                landlord_dicts.append(landlord_dict)
                
                # Also save property data to separate collection
                for property_data in landlord.properties:
                    property_dict = property_data.to_dict()
                    property_dict['landlord_id'] = landlord.landlord_id
                    property_dicts.append(property_dict)
            
            # Insert landlords
            if landlord_dicts:
                self.landlord_client.collection.insert_many(landlord_dicts)
            
            # Insert properties
            if property_dicts:
                self.property_client.collection.insert_many(property_dicts)
            
            # Save tenant data
            tenant_dicts = [tenant.to_dict() for tenant in tenants]
            if tenant_dicts:
                self.tenant_client.collection.insert_many(tenant_dicts)
            
            logger.info(f"Successfully saved {len(landlords)} landlords and {len(tenants)} tenants to MongoDB")
            
        except Exception as e:
            logger.error(f"Failed to save data to MongoDB: {e}")
            raise

    def initialize_all_data(self, rightmove_file_path: str = f"{config.root_path}/dataset/rent_cast_data/processed/rightmove_data_processed.json", tenant_count: int = 50):
        """Initialize all data"""
        logger.info("Starting Agent data initialization...")
        
        # 1. Load property data
        raw_properties = self.load_rightmove_data(rightmove_file_path)
        if not raw_properties:
            logger.error("Cannot load property data, initialization failed")
            return
        
        # 2. Clean property data
        properties = []
        for raw_prop in raw_properties:
            try:
                prop = self.clean_property_data(raw_prop)
                properties.append(prop)
            except Exception as e:
                logger.warning(f"Skipping invalid property data: {e}")
                continue
        
        logger.info(f"Successfully processed {len(properties)} property records")
        
        # 3. Create landlords
        landlords = self.create_landlords_from_properties(properties)
        
        # 4. Create tenants
        tenants = self.create_random_tenants(tenant_count)
        
        # 5. Save to MongoDB
        self.save_to_mongodb(landlords, tenants)
        
        logger.info("Data initialization completed!")
        
        # 6. Print statistics
        # self.print_statistics()
    
    async def clear_all_data(self):
        """清除所有数据"""
        try:
            self.landlord_client.collection.delete_many({})
            self.tenant_client.collection.delete_many({})
            self.property_client.collection.delete_many({})
            logger.info("成功清除所有数据")
        except Exception as e:
            logger.error(f"清除数据失败: {e}")
            raise

    async def get_properties_count(self) -> int:
        """获取房产数量"""
        return self.property_client.collection.count_documents({})

    async def get_landlords_count(self) -> int:
        """获取房东数量"""
        return self.landlord_client.collection.count_documents({})

    async def get_tenants_count(self) -> int:
        """获取租客数量"""
        return self.tenant_client.collection.count_documents({})

    async def initialize_properties_and_landlords(self, rightmove_file_path: str = None):
        """初始化房产和房东数据"""
        if not rightmove_file_path:
            rightmove_file_path = f"{config.root_path}/backend/dataset/rent_cast_data/processed/rightmove_data_processed.json"
        
        try:
            # 加载房产数据
            raw_properties = self.load_rightmove_data(rightmove_file_path)
            if not raw_properties:
                logger.warning("无法从文件加载房产数据，使用默认数据")
                raw_properties = self._get_default_properties()
            
            # 清洁房产数据
            properties = []
            for raw_prop in raw_properties:
                try:
                    prop = self.clean_property_data(raw_prop)
                    properties.append(prop)
                except Exception as e:
                    logger.warning(f"跳过无效房产数据: {e}")
                    continue
            
            if not properties:
                logger.warning("没有有效的房产数据，创建默认房产")
                properties = self._create_default_properties()
            
            # 创建房东
            landlords = self.create_landlords_from_properties(properties)
            
            # 保存房东和房产数据
            landlord_dicts = []
            property_dicts = []
            
            for landlord in landlords:
                landlord_dict = landlord.to_dict()
                landlord_dicts.append(landlord_dict)
                
                # 保存房产数据到独立集合
                for property_data in landlord.properties:
                    property_dict = property_data.to_dict()
                    property_dict['landlord_id'] = landlord.landlord_id
                    property_dicts.append(property_dict)
            
            # 插入数据
            if landlord_dicts:
                self.landlord_client.collection.insert_many(landlord_dicts)
            if property_dicts:
                self.property_client.collection.insert_many(property_dicts)
            
            logger.info(f"成功初始化 {len(landlords)} 个房东和 {len(properties)} 个房产")
            
        except Exception as e:
            logger.error(f"初始化房产和房东数据失败: {e}")
            # 创建基本的默认数据
            await self._create_emergency_data()
    
    def _get_default_properties(self):
        """获取默认房产数据"""
        return [
            {
                "id": "prop_001",
                "bedrooms": 2,
                "price": {"amount": 2500, "frequency": "monthly", "currencyCode": "GBP"},
                "displayAddress": "Central London, W1",
                "location": {"latitude": 51.5074, "longitude": -0.1278},
                "propertySubType": "Apartment"
            },
            {
                "id": "prop_002", 
                "bedrooms": 1,
                "price": {"amount": 1800, "frequency": "monthly", "currencyCode": "GBP"},
                "displayAddress": "Camden, NW1",
                "location": {"latitude": 51.5393, "longitude": -0.1435},
                "propertySubType": "Flat"
            },
            {
                "id": "prop_003",
                "bedrooms": 3,
                "price": {"amount": 3200, "frequency": "monthly", "currencyCode": "GBP"},
                "displayAddress": "Greenwich, SE10",
                "location": {"latitude": 51.4934, "longitude": 0.0098},
                "propertySubType": "House"
            }
        ]
    
    def _create_default_properties(self):
        """创建默认房产对象"""
        from app.agents.models.property_model import PropertyModel
        
        properties = []
        default_data = self._get_default_properties()
        
        for data in default_data:
            prop = PropertyModel(
                property_id=data["id"],
                bedrooms=data["bedrooms"],
                price=data["price"],
                display_address=data["displayAddress"],
                location=data["location"],
                property_sub_type=data["propertySubType"]
            )
            properties.append(prop)
        
        return properties
    
    async def _create_emergency_data(self):
        """创建紧急默认数据"""
        logger.info("创建紧急默认数据...")
        
        # 创建默认房产数据
        default_properties = [
            {
                "property_id": "emergency_001",
                "bedrooms": 2,
                "price": {"amount": 2000, "frequency": "monthly", "currencyCode": "GBP"},
                "display_address": "London Property 1",
                "location": {"latitude": 51.5074, "longitude": -0.1278},
                "property_sub_type": "Apartment",
                "landlord_id": "emergency_landlord_001"
            },
            {
                "property_id": "emergency_002",
                "bedrooms": 1, 
                "price": {"amount": 1500, "frequency": "monthly", "currencyCode": "GBP"},
                "display_address": "London Property 2",
                "location": {"latitude": 51.5200, "longitude": -0.1000},
                "property_sub_type": "Flat",
                "landlord_id": "emergency_landlord_001"
            }
        ]
        
        # 创建默认房东数据
        default_landlords = [
            {
                "landlord_id": "emergency_landlord_001",
                "name": "Default Landlord",
                "phone": "+44 20 1234 5678",
                "branch_name": "London Properties",
                "properties": [],
                "preferences": {"pet_friendly": True, "smoking_allowed": False, "deposit_weeks": 6}
            }
        ]
        
        # 插入数据
        if default_properties:
            self.property_client.collection.insert_many(default_properties)
        if default_landlords:
            self.landlord_client.collection.insert_many(default_landlords)
            
        logger.info("紧急默认数据创建完成")

    async def generate_tenants(self, count: int) -> List[Dict[str, Any]]:
        """生成指定数量的租客"""
        tenants = self.create_random_tenants(count)
        
        # 保存到数据库
        tenant_dicts = [tenant.to_dict() for tenant in tenants]
        if tenant_dicts:
            self.tenant_client.collection.insert_many(tenant_dicts)
        
        logger.info(f"成功生成 {len(tenants)} 个租客")
        # 转换ObjectId为字符串
        return [self._convert_objectid_to_str(tenant_dict) for tenant_dict in tenant_dicts]

    def _convert_objectid_to_str(self, data):
        """递归转换ObjectId为字符串"""
        from bson import ObjectId
        
        if isinstance(data, ObjectId):
            return str(data)
        elif isinstance(data, dict):
            return {key: self._convert_objectid_to_str(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_objectid_to_str(item) for item in data]
        else:
            return data

    async def get_all_properties(self) -> List[Dict[str, Any]]:
        """获取所有房产数据"""
        properties = list(self.property_client.collection.find({}))
        # 转换ObjectId为字符串
        return [self._convert_objectid_to_str(prop) for prop in properties]

    async def get_all_landlords(self) -> List[Dict[str, Any]]:
        """获取所有房东数据"""
        landlords = list(self.landlord_client.collection.find({}))
        # 转换ObjectId为字符串
        return [self._convert_objectid_to_str(landlord) for landlord in landlords]

    async def get_all_tenants(self) -> List[Dict[str, Any]]:
        """获取所有租客数据"""
        tenants = list(self.tenant_client.collection.find({}))
        # 转换ObjectId为字符串
        return [self._convert_objectid_to_str(tenant) for tenant in tenants]

    def print_statistics(self):
        """Print data statistics"""
        try:
            landlord_count = self.landlord_client.collection.count_documents({})
            tenant_count = self.tenant_client.collection.count_documents({})
            property_count = self.property_client.collection.count_documents({})
            
            logger.info("=== Data Statistics ===")
            logger.info(f"Number of Landlords: {landlord_count}")
            logger.info(f"Number of Tenants: {tenant_count}")
            logger.info(f"Number of Properties: {property_count}")
            
            # Property type statistics
            pipeline = [
                {"$group": {"_id": "$property_sub_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            property_types = list(self.property_client.collection.aggregate(pipeline))
            logger.info("Property Type Distribution:")
            for pt in property_types:
                logger.info(f"  {pt['_id']}: {pt['count']}")
            
            # Price range statistics
            pipeline = [
                {"$group": {
                    "_id": {
                        "$switch": {
                            "branches": [
                                {"case": {"$lt": ["$price.amount", 2000]}, "then": "< £2000"},
                                {"case": {"$lt": ["$price.amount", 3000]}, "then": "£2000-3000"},
                                {"case": {"$lt": ["$price.amount", 4000]}, "then": "£3000-4000"},
                                {"case": {"$gte": ["$price.amount", 4000]}, "then": "> £4000"}
                            ],
                            "default": "Unknown"
                        }
                    },
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]
            price_ranges = list(self.property_client.collection.aggregate(pipeline))
            logger.info("Price Range Distribution:")
            for pr in price_ranges:
                logger.info(f"  {pr['_id']}: {pr['count']}")
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")


if __name__ == "__main__":
    # Initialize data
    initializer = AgentDataInitializer()
    
    # Use actual JSON file path
    rightmove_file = f"{config.root_path}/backend/dataset/rent_cast_data/processed/rightmove_data_processed.json"

    # Initialize all data
    initializer.initialize_all_data(rightmove_file, tenant_count=50)
