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
            unique_properties = []
            for prop in data:
                # Using property ID as the unique identifier
                prop_id = prop.get('propertyId')
                unique_properties.append(prop)

            deduplicated_data = unique_properties
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
        """Create landlords: new customer -> new landlord, else append property to existing landlord"""
        landlord_map = {}  # key: customer_key, value: LandlordModel
        for prop in properties:
            customer = getattr(prop, 'customer', None)
            if isinstance(customer, dict):
                brand = customer.get('branchDisplayName')
                branch_id = customer.get('branchId')
                if brand and branch_id:
                    customer_key = f"{brand}_{branch_id}"
                elif brand:
                    customer_key = brand
                else:
                    customer_key = 'unknown_landlord'
            else:
                customer_key = 'unknown_landlord'

            if customer_key not in landlord_map:
                name = None
                phone = None
                branch_name = None
                if isinstance(customer, dict):
                    name = customer.get('branchDisplayName') or customer_key
                    phone = customer.get('contactTelephone') or customer.get('telephoneNumber') or customer.get('phone')
                    branch_name = customer.get('branchDisplayName') or customer.get('branchName')
                if not name:
                    name = customer_key
                if not branch_name:
                    branch_name = 'Unknown Branch'
                if not phone:
                    phone = self.fake.phone_number()
                preferences = {
                    'pet_friendly': random.choice([True, False]),
                    'smoking_allowed': random.choice([True, False]),
                    'deposit_weeks': random.choice([4, 5, 6])
                }
                landlord = LandlordModel(
                    name=name,
                    phone=phone,
                    branch_name=branch_name,
                    properties=[prop],
                    preferences=preferences
                )
                landlord_map[customer_key] = landlord
            else:
                landlord_map[customer_key].properties.append(prop)
        landlords = list(landlord_map.values())
        logger.info(f"Created {len(landlords)} landlords (unique customer)")
        return landlords
    
    def create_random_tenants(self, count: int = 200) -> List[TenantModel]:
        """Create realistic student tenants for London based on 2024 survey"""
        tenants = []
        # 伦敦主要大学及周边区域
        uni_areas = [
            {"latitude": 51.5246, "longitude": -0.1340, "name": "UCL/Bloomsbury"},
            {"latitude": 51.5220, "longitude": -0.1300, "name": "SOAS/Bloomsbury"},
            {"latitude": 51.4988, "longitude": -0.1749, "name": "Imperial/South Kensington"},
            {"latitude": 51.5116, "longitude": -0.1160, "name": "LSE/Aldwych"},
            {"latitude": 51.5380, "longitude": -0.1025, "name": "City/Islington"},
            {"latitude": 51.4882, "longitude": -0.1106, "name": "KCL/Waterloo"},
            {"latitude": 51.5560, "longitude": -0.2795, "name": "Brunel/Uxbridge"},
            {"latitude": 51.4452, "longitude": -0.1248, "name": "Goldsmiths/New Cross"},
            {"latitude": 51.5219, "longitude": -0.1382, "name": "Regent's Park"},
            {"latitude": 51.5007, "longitude": -0.1246, "name": "Westminster"}
        ]
        for _ in range(count):
            # 预算分布（2024伦敦学生宿舍市场真实分布）
            budget = int(random.choices(
                population=[800, 900, 1000, 1100, 1200, 1300, 1400, 1500],
                weights=[10, 20, 30, 25, 20, 10, 3, 2],  # £900-£1200为主流
                k=1
            )[0])
            # 年收入（假设家庭/奖学金/兼职，3-5倍月租，部分有担保人）
            annual_income = budget * 12 * random.uniform(3.0, 5.0)
            # 偏好1-2人间
            min_bedrooms = 1
            max_bedrooms = random.choices([1, 2], weights=[0.7, 0.3])[0]
            # 偏好大学周边
            num_preferred = random.randint(1, 2)
            preferred_locations = []
            for coord in random.sample(uni_areas, num_preferred):
                lat_variation = random.uniform(-0.005, 0.005)
                lon_variation = random.uniform(-0.005, 0.005)
                preferred_locations.append({
                    "latitude": coord["latitude"] + lat_variation,
                    "longitude": coord["longitude"] + lon_variation
                })
            # 其它属性
            is_student = True
            has_pets = random.choices([False, True], weights=[0.85, 0.15])[0]
            is_smoker = random.choices([False, True], weights=[0.9, 0.1])[0]
            has_guarantor = True  # 绝大多数学生有担保人
            num_occupants = random.choices([1, 2], weights=[0.8, 0.2])[0]
            tenant = TenantModel(
                name=self.fake.name(),
                email=self.fake.email(),
                phone=self.fake.phone_number(),
                annual_income=annual_income,
                has_guarantor=has_guarantor,
                max_budget=budget,
                min_bedrooms=min_bedrooms,
                max_bedrooms=max_bedrooms,
                preferred_locations=preferred_locations,
                is_student=is_student,
                has_pets=has_pets,
                is_smoker=is_smoker,
                num_occupants=num_occupants
            )
            tenants.append(tenant)
        logger.info(f"Created {len(tenants)} student tenants (realistic London distribution)")
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
        logger.info(f"Loaded {len(raw_properties)} raw property records")
        
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
            rightmove_file_path = f"{config.root_path}/dataset/rent_cast_data/processed/rightmove_data_processed.json"
        
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
        
        # Save to database
        tenant_dicts = [tenant.to_dict() for tenant in tenants]
        if tenant_dicts:
            self.tenant_client.collection.insert_many(tenant_dicts)
        
        logger.info(f"Successfully generated {len(tenants)} tenants")
        # Convert ObjectId to string
        return [self._convert_objectid_to_str(tenant_dict) for tenant_dict in tenant_dicts]

    def _convert_objectid_to_str(self, data):
        """Recursively convert ObjectId to string"""
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
        """Get all property data"""
        properties = list(self.property_client.collection.find({}))
        # Convert ObjectId to string
        return [self._convert_objectid_to_str(prop) for prop in properties]

    async def get_all_landlords(self) -> List[Dict[str, Any]]:
        """Get all landlord data"""
        landlords = list(self.landlord_client.collection.find({}))
        # Convert ObjectId to string
        return [self._convert_objectid_to_str(landlord) for landlord in landlords]

    async def get_all_tenants(self) -> List[Dict[str, Any]]:
        """Get all tenant data"""
        tenants = list(self.tenant_client.collection.find({}))
        # Convert ObjectId to string
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
    rightmove_file = f"{config.root_path}/dataset/rent_cast_data/processed/rightmove_data_processed.json"

    # Initialize all data
    initializer.initialize_all_data(rightmove_file, tenant_count=50)
