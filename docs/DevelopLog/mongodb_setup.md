# MongoDB 开发环境配置

本文档描述了Rental Agent项目中MongoDB本地开发环境的配置和使用方法。

## 📋 配置概览

### Docker Compose 配置

```yaml
version: '3.8'

services:
  mongodb:
    image: mongo:7.0
    container_name: rental_mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: admin123
      MONGO_INITDB_DATABASE: rental_agent
    volumes:
      - mongodb_data:/data/db
    command: mongod --bind_ip_all

volumes:
  mongodb_data:
```

### 项目配置 (config/config.toml)

```toml
[mongodb]
host = "localhost"
port = 27017
username = "admin"
password = "admin123"
database = "rental_agent"
```

## 🚀 使用方法

### 启动MongoDB容器

```bash
# 在项目根目录下启动MongoDB容器
docker-compose up -d

# 查看容器状态
docker-compose ps

# 查看MongoDB日志
docker-compose logs mongodb
```

### 停止MongoDB容器

```bash
# 停止容器（保留数据）
docker-compose down

# 停止容器并删除数据
docker-compose down -v

# 重启容器
docker-compose restart mongodb
```

## 🔧 连接MongoDB

### 使用MongoDB Shell

```bash
# 进入MongoDB容器的shell
docker exec -it rental_mongodb mongosh -u admin -p admin123

# 或者从宿主机连接（需要安装mongosh）
mongosh "mongodb://admin:admin123@localhost:27017/rental_agent"
```

### Python连接示例

```python
from pymongo import MongoClient

# 基本连接
client = MongoClient("mongodb://admin:admin123@localhost:27017/")
db = client.rental_agent

# 使用项目配置
from app.config import config
from app.mongodb import MongoClientWrapper

mongo_client = MongoClientWrapper(config.mongodb)
db = mongo_client.get_database()
```

## 📊 数据库结构

### 集合设计

项目中使用以下主要集合：

- `rental_properties` - 房源信息
- `rental_agreements` - 租赁协议
- `market_analysis` - 市场分析数据
- `user_preferences` - 用户偏好设置

### 数据模型

详细的数据模型定义请参考 `app/mongodb/models.py`：

- `RentalProperty` - 房源属性模型
- `RentalAgreement` - 租赁协议模型
- `MarketAnalysis` - 市场分析模型
- `UserPreference` - 用户偏好模型

## 🛠️ 开发工具

### 数据库服务

使用 `RentalDatabaseService` 类进行高级数据库操作：

```python
from app.mongodb import RentalDatabaseService

# 初始化服务
db_service = RentalDatabaseService()

# 添加房源
property_data = {...}
property_id = db_service.add_property(property_data)

# 查询房源
properties = db_service.find_properties_by_criteria({
    "price_range": (1000, 2000),
    "bedrooms": 2
})
```

### 索引管理

项目自动创建以下索引以优化查询性能：

- 地理位置索引（2dsphere）
- 价格范围索引
- 房型索引
- 全文搜索索引

## 🔍 常用操作

### 查看数据库状态

```javascript
// 在MongoDB shell中执行
use rental_agent;

// 查看所有集合
show collections;

// 查看集合文档数量
db.rental_properties.countDocuments();

// 查看索引
db.rental_properties.getIndexes();
```

### 数据导入导出

```bash
# 导出数据
docker exec rental_mongodb mongodump -u admin -p admin123 --authenticationDatabase admin -d rental_agent -o /data/backup

# 导入数据
docker exec rental_mongodb mongorestore -u admin -p admin123 --authenticationDatabase admin /data/backup
```

## ⚠️ 注意事项

1. **开发环境专用**: 此配置仅适用于开发环境，生产环境需要更强的安全配置
2. **数据持久化**: 数据通过Docker volume持久化，删除容器不会丢失数据
3. **端口冲突**: 确保本地27017端口未被占用
4. **内存使用**: MongoDB可能占用较多内存，建议分配足够的Docker资源

## 🐛 故障排除

### 常见问题

1. **容器启动失败**
   ```bash
   # 检查端口占用
   lsof -i :27017
   
   # 检查Docker日志
   docker-compose logs mongodb
   ```

2. **连接被拒绝**
   ```bash
   # 确保容器正在运行
   docker ps | grep rental_mongodb
   
   # 检查防火墙设置
   sudo ufw status
   ```

3. **权限问题**
   ```bash
   # 确保Docker有足够权限
   sudo docker-compose up -d
   ```

## 📚 相关文档

- [MongoDB官方文档](https://docs.mongodb.com/)
- [PyMongo文档](https://pymongo.readthedocs.io/)
- [项目API文档](../docs/api/)

---

*更新时间: 2025-05-28*
