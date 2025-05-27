# 基于AutoGen的租房市场智能体系统设计

## 1. 系统架构设计

### 核心智能体类型
```python
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
import requests
from booking_api_client import BookingAPIClient

# 租客智能体
class TenantAgent(AssistantAgent):
    def __init__(self, tenant_profile):
        self.budget = tenant_profile["budget"]
        self.preferences = tenant_profile["preferences"]  # 地段、户型、设施等
        self.current_situation = tenant_profile["situation"]
        self.urgency = tenant_profile["urgency"]
        self.search_history = []
        self.viewed_properties = []
        
# 房东智能体  
class LandlordAgent(AssistantAgent):
    def __init__(self, landlord_profile):
        self.properties = landlord_profile["properties"]
        self.pricing_strategy = landlord_profile["pricing_strategy"]
        self.tenant_preferences = landlord_profile["tenant_preferences"]
        self.booking_listings = []  # Booking.com上的房源
        
# 市场分析师智能体
class MarketAnalystAgent(AssistantAgent):
    def __init__(self):
        self.booking_api = BookingAPIClient()
        self.market_data = {}
        self.price_trends = {}
        self.supply_demand = {}
        self.real_time_data = {}
        
# 房源数据智能体 (新增)
class PropertyDataAgent(AssistantAgent):
    def __init__(self, api_credentials):
        self.booking_api = BookingAPIClient(api_credentials)
        self.property_cache = {}
        self.search_cache = {}
        self.last_update = None
```

## 2. Booking.com API集成

### 2.1 实时房源数据获取
```python
class BookingAPIClient:
    def __init__(self, api_key, base_url="https://distribution-xml.booking.com/"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        
    def search_properties(self, search_params):
        """
        搜索房源
        search_params: {
            'checkin': '2025-06-01',
            'checkout': '2025-06-30', 
            'city_id': 'beijing',
            'guests': 2,
            'property_type': 'apartment',
            'price_min': 1000,
            'price_max': 5000
        }
        """
        endpoint = f"{self.base_url}json/bookings.getHotels"
        params = {
            'hotel_id': search_params.get('hotel_id'),
            'checkin': search_params['checkin'],
            'checkout': search_params['checkout'],
            'currency': 'CNY',
            'language': 'zh-cn',
            'extras': 'hotel_details,room_info,hotel_photos'
        }
        
        response = self.session.get(endpoint, params=params)
        return response.json()
        
    def get_property_details(self, property_id):
        """获取房源详细信息"""
        endpoint = f"{self.base_url}json/bookings.getHotelDescriptionTranslated"
        params = {
            'hotel_id': property_id,
            'language': 'zh-cn'
        }
        
        response = self.session.get(endpoint, params=params)
        return response.json()
        
    def get_availability_calendar(self, property_id, start_date, end_date):
        """获取房源可用性日历"""
        endpoint = f"{self.base_url}json/bookings.getHotelAvailabilityV2"
        params = {
            'hotel_id': property_id,
            'checkin': start_date,
            'checkout': end_date,
            'currency': 'CNY'
        }
        
        response = self.session.get(endpoint, params=params)
        return response.json()
        
    def get_reviews(self, property_id, limit=50):
        """获取房源评价"""
        endpoint = f"{self.base_url}json/bookings.getHotelReviews"
        params = {
            'hotel_id': property_id,
            'limit': limit,
            'language': 'zh-cn'
        }
        
        response = self.session.get(endpoint, params=params)
        return response.json()
```

### 2.2 数据预处理与标准化
```python
class PropertyDataProcessor:
    def __init__(self):
        self.standardized_fields = {
            'id', 'name', 'address', 'price_per_night',
            'property_type', 'bedrooms', 'bathrooms', 'amenities',
            'photos', 'reviews_score', 'availability'
        }
        
    def standardize_booking_data(self, booking_property):
        """将Booking.com数据标准化为内部格式"""
        return {
            'id': booking_property.get('hotel_id'),
            'name': booking_property.get('hotel_name'),
            'address': booking_property.get('address'),
            'price_per_night': booking_property.get('min_total_price'),
            'property_type': self._map_property_type(booking_property.get('accommodation_type')),
            'bedrooms': self._extract_bedrooms(booking_property),
            'bathrooms': self._extract_bathrooms(booking_property),
            'amenities': booking_property.get('facilities', []),
            'photos': booking_property.get('main_photo_url'),
            'reviews_score': booking_property.get('review_score'),
            'availability': self._check_availability(booking_property),
            'location': {
                'latitude': booking_property.get('latitude'),
                'longitude': booking_property.get('longitude'),
                'city': booking_property.get('city'),
                'district': booking_property.get('district')
            }
        }
        
    def _map_property_type(self, booking_type):
        """映射Booking.com房源类型到内部类型"""
        type_mapping = {
            'hotel': '酒店',
            'apartment': '公寓',
            'house': '别墅',
            'guesthouse': '民宿',
            'hostel': '青年旅舍'
        }
        return type_mapping.get(booking_type, '其他')
        
    def calculate_monthly_rent(self, nightly_rate, occupancy_rate=0.8):
        """根据日租金计算月租金估算"""
        return nightly_rate * 30 * occupancy_rate
```

## 3. 认知架构适配

### 原项目认知模块 → AutoGen适配

#### 感知模块 (Perceive) → 实时数据监听
```python
def perceive_market_events(self, messages):
    """监听市场事件：新房源、价格变动、政策变化等"""
    relevant_events = []
    
    # 监听Booking.com实时数据更新
    new_properties = self.booking_api.get_latest_updates()
    price_changes = self.booking_api.get_price_changes()
    
    for msg in messages:
        if self.is_relevant_to_me(msg):
            relevant_events.append(msg)
            
    # 整合实时房源数据
    for prop in new_properties:
        relevant_events.append({
            'type': 'new_property',
            'data': prop,
            'timestamp': datetime.now()
        })
        
    return relevant_events
```

#### 检索模块 (Retrieve) → 智能房源匹配
```python
def retrieve_relevant_properties(self, tenant_preferences):
    """基于租客偏好检索匹配房源"""
    search_params = {
        'checkin': tenant_preferences.get('move_in_date'),
        'checkout': tenant_preferences.get('lease_end_date'),
        'city_id': tenant_preferences.get('preferred_city'),
        'guests': tenant_preferences.get('occupants'),
        'price_max': tenant_preferences.get('budget'),
        'property_type': tenant_preferences.get('property_type')
    }
    
    # 从Booking.com API获取实时数据
    raw_properties = self.booking_api.search_properties(search_params)
    
    # 使用向量相似度匹配用户偏好
    matched_properties = self._semantic_match(
        raw_properties, 
        tenant_preferences['preferences_text']
    )
    
    return matched_properties
    
def _semantic_match(self, properties, preferences_text):
    """使用embedding进行语义匹配"""
    # 实现基于向量相似度的房源匹配
    pass
```

#### 规划模块 (Plan) → 数据驱动策略制定
```python
def plan_rental_strategy(self, market_info, personal_constraints):
    """
    租客：基于实时市场数据制定看房计划、出价策略
    房东：基于竞争对手数据制定定价策略、租客筛选标准
    """
    if self.agent_type == "tenant":
        return self._plan_tenant_strategy(market_info, personal_constraints)
    elif self.agent_type == "landlord":
        return self._plan_landlord_strategy(market_info, personal_constraints)
        
def _plan_tenant_strategy(self, market_info, constraints):
    """租客策略：基于实时价格分析制定预算和看房计划"""
    avg_price = market_info['average_price']
    price_trend = market_info['price_trend']
    supply_level = market_info['supply_level']
    
    strategy = {
        'budget_adjustment': self._calculate_budget_adjustment(avg_price, constraints['budget']),
        'urgency_level': self._assess_market_urgency(supply_level, price_trend),
        'viewing_priority': self._prioritize_viewings(market_info['hot_properties']),
        'negotiation_range': self._calculate_negotiation_range(avg_price)
    }
    
    return strategy
    
def _plan_landlord_strategy(self, market_info, constraints):
    """房东策略：基于竞争分析制定定价和筛选标准"""
    competitor_prices = market_info['competitor_analysis']
    demand_level = market_info['demand_level']
    
    strategy = {
        'pricing_strategy': self._optimize_pricing(competitor_prices, demand_level),
        'tenant_screening': self._define_screening_criteria(demand_level),
        'marketing_channels': self._select_marketing_channels(market_info),
        'lease_terms': self._optimize_lease_terms(market_info)
    }
    
    return strategy
```

#### 执行模块 (Execute) → 智能交互执行
```python
def execute_rental_action(self, plan):
    """
    发送消息：询价、预约看房、提交申请、谈判等
    集成实时数据进行智能决策
    """
    action_type = plan['action_type']
    
    if action_type == "property_inquiry":
        return self._execute_property_inquiry(plan)
    elif action_type == "price_negotiation":
        return self._execute_price_negotiation(plan)
    elif action_type == "viewing_request":
        return self._execute_viewing_request(plan)
        
def _execute_property_inquiry(self, plan):
    """执行房源询价，集成实时市场数据"""
    property_id = plan['property_id']
    
    # 获取最新房源信息
    current_info = self.booking_api.get_property_details(property_id)
    market_comparison = self._get_market_comparison(property_id)
    
    inquiry_message = f"""
    我对您在{current_info['address']}的房源很感兴趣。
    根据市场调研，类似房源的平均价格是{market_comparison['avg_price']}元/月。
    请问我们可以进一步讨论租金和租期吗？
    """
    
    return {
        'message': inquiry_message,
        'data_support': market_comparison,
        'confidence_level': self._calculate_confidence(market_comparison)
    }
```

#### 反思模块 (Reflect) → 数据驱动经验总结
```python
def reflect_on_interaction(self, interaction_history):
    """基于实际交易数据总结租房交互经验，更新策略"""
    
    # 分析成功和失败的交互
    successful_interactions = [i for i in interaction_history if i['outcome'] == 'success']
    failed_interactions = [i for i in interaction_history if i['outcome'] == 'failed']
    
    # 对比当时的市场数据和决策
    market_context_analysis = self._analyze_market_context(interaction_history)
    
    # 更新决策模型
    strategy_updates = {
        'price_sensitivity': self._update_price_sensitivity(successful_interactions),
        'timing_optimization': self._update_timing_strategy(interaction_history),
        'communication_style': self._update_communication_preferences(interaction_history),
        'market_prediction': self._update_market_prediction_model(market_context_analysis)
    }
    
    return strategy_updates
```

## 4. 群聊工作流设计

### 4.1 房源发布与匹配流程
```python
# 移除中介，直接连接租客与房东
rental_market_chat = GroupChat(
    agents=[landlord, property_data_agent, market_analyst, *tenants],
    messages=[],
    max_round=50
)

# 新工作流：实时数据获取 → 智能匹配 → 直接谈判 → 合同签署
class RentalWorkflow:
    def __init__(self):
        self.booking_api = BookingAPIClient()
        self.data_processor = PropertyDataProcessor()
        
    def execute_matching_workflow(self):
        # 1. 获取实时房源数据
        raw_properties = self.booking_api.search_properties(search_params)
        
        # 2. 数据标准化和增强
        processed_properties = [
            self.data_processor.standardize_booking_data(prop) 
            for prop in raw_properties
        ]
        
        # 3. 智能匹配租客需求
        for tenant in active_tenants:
            matched_properties = self.semantic_match(
                processed_properties, 
                tenant.preferences
            )
            
            # 4. 发起群聊匹配
            self.initiate_tenant_landlord_chat(tenant, matched_properties)
            
    def initiate_tenant_landlord_chat(self, tenant, properties):
        """发起租客与房东的直接对话"""
        relevant_landlords = [
            landlord for landlord in landlords 
            if any(prop['owner_id'] == landlord.id for prop in properties)
        ]
        
        chat_group = GroupChat(
            agents=[tenant, market_analyst] + relevant_landlords,
            messages=[],
            max_round=30,
            speaker_selection_method="auto"
        )
        
        return chat_group
```

### 4.2 智能谈判机制
```python
class SmartNegotiationManager:
    def __init__(self):
        self.market_analyzer = MarketAnalystAgent()
        self.negotiation_history = []
        
    def facilitate_negotiation(self, tenant, landlord, property_id):
        """基于实时市场数据促进谈判"""
        
        # 获取市场比较数据
        market_data = self.market_analyzer.get_comparative_analysis(property_id)
        
        negotiation_chat = GroupChat(
            agents=[tenant, landlord, self.market_analyzer],
            messages=[],
            max_round=20,
            speaker_selection_method="round_robin"
        )
        
        # 注入市场数据作为谈判参考
        initial_message = f"""
        基于最新市场数据分析：
        - 该区域平均租金：{market_data['avg_rent']}/月
        - 类似房源价格区间：{market_data['price_range']}
        - 市场供需状况：{market_data['supply_demand_ratio']}
        - 建议合理价格：{market_data['suggested_price']}
        
        让我们开始基于数据的理性谈判。
        """
        
        negotiation_chat.messages.append({
            "role": "system",
            "content": initial_message
        })
        
        return negotiation_chat
        
    def track_negotiation_success(self, negotiation_result):
        """跟踪谈判成功率，优化策略"""
        self.negotiation_history.append(negotiation_result)
        return self._analyze_success_patterns()
```

## 5. 记忆系统设计

### 5.1 分布式记忆架构 + 实时数据缓存
```python
# 每个智能体的记忆系统
class AgentMemory:
    def __init__(self):
        self.spatial_memory = {}  # 房产位置、区域信息
        self.interaction_memory = []  # 交易历史、对话记录
        self.market_memory = {}  # 价格趋势、政策变化
        self.personal_memory = {}  # 个人偏好、经验教训
        self.booking_data_cache = {}  # Booking.com数据缓存
        self.last_sync_time = None
        
    def sync_with_booking_data(self):
        """同步Booking.com最新数据"""
        if self._should_refresh_cache():
            self.booking_data_cache = self._fetch_latest_booking_data()
            self.last_sync_time = datetime.now()
            
    def _should_refresh_cache(self):
        """判断是否需要刷新缓存（每小时更新一次）"""
        if not self.last_sync_time:
            return True
        return datetime.now() - self.last_sync_time > timedelta(hours=1)
```

### 5.2 实时市场知识库
```python
class RealTimeMarketKnowledgeBase:
    def __init__(self):
        self.booking_api = BookingAPIClient()
        self.property_database = {}  # 实时房产信息
        self.price_history = {}  # 历史价格数据
        self.availability_calendar = {}  # 实时可用性
        self.market_trends = {}  # 市场趋势分析
        self.competitor_analysis = {}  # 竞争对手分析
        
    def update_market_intelligence(self):
        """更新市场情报"""
        # 获取最新房源数据
        latest_properties = self.booking_api.get_latest_updates()
        
        # 分析价格趋势
        self._analyze_price_trends(latest_properties)
        
        # 更新供需分析
        self._update_supply_demand_analysis()
        
        # 竞争对手分析
        self._analyze_competitor_strategies()
        
    def get_market_insights(self, location, property_type):
        """获取特定区域和类型的市场洞察"""
        return {
            'average_price': self._calculate_average_price(location, property_type),
            'price_trend': self._get_price_trend(location, property_type),
            'supply_level': self._assess_supply_level(location, property_type),
            'demand_indicators': self._analyze_demand(location, property_type),
            'seasonal_patterns': self._identify_seasonal_patterns(location),
            'competitor_pricing': self._get_competitor_pricing(location, property_type)
        }
```

## 6. 环境与可视化

### 6.1 虚拟租房环境 + 实时数据集成
- **地图系统**：集成Booking.com地理信息的城市区域、交通、配套设施
- **房产系统**：实时房源信息、状态跟踪、价格变动监控
- **市场系统**：基于真实数据的供需关系、价格变动分析

### 6.2 增强可视化界面
```python
# 使用Streamlit构建实时数据展示界面
class RealTimeRentalMarketUI:
    def __init__(self):
        self.booking_api = BookingAPIClient()
        self.map_view = {}  # 实时房源地图
        self.chat_view = {}  # 智能体对话
        self.analytics_view = {}  # 实时市场分析图表
        self.booking_integration = {}  # Booking.com数据展示
        
    def render_real_time_dashboard(self):
        """渲染实时数据仪表板"""
        st.title("智能租房市场 - 实时数据分析")
        
        # 实时房源地图
        with st.container():
            st.subheader("实时房源分布")
            self._render_property_map()
            
        # 价格趋势图
        with st.container():
            st.subheader("价格趋势分析")
            self._render_price_trends()
            
        # 智能体对话面板
        with st.container():
            st.subheader("智能体协商过程")
            self._render_agent_conversations()
            
    def _render_property_map(self):
        """渲染实时房源地图"""
        # 获取最新房源数据
        properties = self.booking_api.get_all_properties()
        
        # 使用Folium创建交互式地图
        map_data = self._prepare_map_data(properties)
        st_folium(map_data, width=1000, height=500)
        
    def _render_price_trends(self):
        """渲染价格趋势图表"""
        price_data = self.booking_api.get_price_history()
        
        fig = px.line(
            price_data, 
            x='date', 
            y='average_price',
            color='property_type',
            title='不同类型房源价格趋势'
        )
        st.plotly_chart(fig, use_container_width=True)
```

## 7. 具体实现步骤

### 阶段1：Booking.com API集成
1. 申请Booking.com开发者账户和API密钥
2. 实现BookingAPIClient类和数据处理模块
3. 构建实时数据同步机制
4. 设计数据标准化流程

### 阶段2：智能体框架搭建
1. 基于AutoGen实现核心智能体（移除中介）
2. 集成Booking.com数据到智能体决策流程
3. 实现基于实时数据的匹配算法
4. 构建智能谈判机制

### 阶段3：认知能力增强
1. 添加基于实时数据的记忆系统
2. 实现数据驱动的决策算法
3. 集成市场预测模型
4. 优化智能体学习能力

### 阶段4：可视化与分析
1. 开发实时数据展示界面
2. 实现交互式地图和图表
3. 构建智能体行为分析工具
4. 添加市场洞察报告功能

## 8. 技术栈更新

```python
# 核心框架
- AutoGen: 多智能体对话框架
- LangChain: LLM应用开发
- ChromaDB/Pinecone: 向量数据库存储记忆

# 数据处理与API集成
- Booking.com API: 实时房源数据
- Pandas: 数据处理和分析
- NumPy: 数值计算
- Scikit-learn: 机器学习和预测模型
- Requests: API调用和数据获取

# 可视化与界面
- Streamlit: 实时Web应用框架
- Plotly: 交互式数据可视化
- Folium: 地图可视化
- st-folium: Streamlit地图组件

# 数据存储与缓存
- Redis: 实时数据缓存
- PostgreSQL: 历史数据存储
- SQLAlchemy: 数据库ORM

# 监控与分析
- APScheduler: 定时任务调度
- Logging: 系统日志记录
- Prometheus: 性能监控
```

## 9. 关键创新点

1. **真实数据驱动**：基于Booking.com实时数据进行决策，提高系统实用性
2. **去中介化设计**：租客与房东直接对接，减少中间环节，提高效率
3. **智能价格发现**：利用实时市场数据进行动态定价和谈判
4. **个性化匹配**：结合用户偏好和市场数据进行精准推荐
5. **预测性分析**：基于历史数据和趋势进行市场预测
6. **实时响应机制**：快速响应市场变化和政策调整
7. **数据可视化**：直观展示市场动态和智能体行为

## 10. 商业价值与应用场景

### 10.1 目标用户群体
- **个人租客**：寻找合适房源，获得市场价格指导
- **房东业主**：优化定价策略，快速找到合适租客
- **房产投资者**：市场分析和投资决策支持
- **政策制定者**：房地产市场监管和政策影响分析

### 10.2 核心功能价值
- **实时市场情报**：基于真实数据的价格趋势和供需分析
- **智能匹配引擎**：提高租房效率，减少搜索时间
- **公平价格发现**：透明的市场数据支持合理定价
- **风险评估**：基于历史数据评估租赁风险
- **政策影响分析**：预测政策变化对市场的影响

这个重新设计的系统将AutoGen的多智能体能力与Booking.com的真实数据相结合，创建一个更加实用、高效且数据驱动的租房市场仿真平台。通过移除中介环节，系统变得更加简洁有效，同时实时数据的集成大大提升了系统的实用价值。
