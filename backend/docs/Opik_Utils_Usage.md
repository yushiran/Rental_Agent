# Opik Utils 使用指南

简洁高效的 Opik 集成工具，用于监控和追踪 LLM 调用。

## 配置

### 1. 配置文件设置

在 `config/config.toml` 中添加 Opik 配置：

```toml
[opik]
api_key = "your_opik_api_key"
workspace = "your_workspace_name"
project_name = "rental_agent"
use_local = false
# base_url = "http://localhost:3000"  # 如果使用本地实例
```

### 2. 初始化配置

在应用启动时调用配置函数：

```python
from app.utils.opik_utils import configure

# 在应用启动时调用
configure()
```

## 功能使用

### 1. LLM 调用追踪

使用装饰器追踪 LLM 调用：

```python
from app.utils.opik_utils import track_llm_call

@track_llm_call("rental_analysis")
def analyze_rental_market(query: str) -> str:
    # 你的 LLM 调用逻辑
    response = llm.invoke(query)
    return response

# 或者使用默认名称（函数名）
@track_llm_call()
def generate_contract(tenant_info: dict) -> str:
    # 这将被追踪为 "generate_contract"
    return llm.invoke(prompt.format(**tenant_info))
```

### 2. 数据集管理

#### 创建数据集

```python
from app.utils.opik_utils import create_dataset

# 准备数据
evaluation_data = [
    {
        "input": "Find 2-bedroom apartments in London",
        "expected_output": "Here are available 2-bedroom apartments...",
        "context": "London rental market data"
    },
    {
        "input": "Generate lease agreement for John Doe",
        "expected_output": "Lease Agreement for John Doe...",
        "context": "Standard lease template"
    }
]

# 创建数据集
dataset = create_dataset(
    name="rental_evaluation_set",
    description="Evaluation dataset for rental agent responses",
    items=evaluation_data
)
```

#### 获取现有数据集

```python
from app.utils.opik_utils import get_dataset

# 获取数据集
dataset = get_dataset("rental_evaluation_set")
if dataset:
    print(f"Dataset found with {len(dataset)} items")
else:
    print("Dataset not found")
```

## 实际应用示例

### 1. 租赁分析代理

```python
from app.utils.opik_utils import track_llm_call

class RentalAnalyst:
    @track_llm_call("market_analysis")
    def analyze_market_trends(self, location: str, property_type: str) -> dict:
        prompt = f"Analyze rental market trends for {property_type} in {location}"
        
        # LLM 调用
        response = self.llm.invoke(prompt)
        
        # 返回结构化数据
        return {
            "location": location,
            "property_type": property_type,
            "analysis": response,
            "timestamp": datetime.now().isoformat()
        }
    
    @track_llm_call("price_prediction")
    def predict_rental_price(self, property_details: dict) -> float:
        # 价格预测逻辑
        pass
```

### 2. 合同生成服务

```python
from app.utils.opik_utils import track_llm_call

class ContractGenerator:
    @track_llm_call("contract_generation")
    def generate_lease_agreement(self, tenant_info: dict, property_info: dict) -> str:
        # 生成租赁合同
        template = self.get_contract_template()
        
        # 使用 LLM 填充模板
        filled_contract = self.llm.invoke({
            "template": template,
            "tenant_info": tenant_info,
            "property_info": property_info
        })
        
        return filled_contract
```

### 3. 应用启动配置

```python
# main.py
from app.utils.opik_utils import configure

def main():
    # 配置 Opik
    configure()
    
    # 启动应用
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
```

## 特点

1. **简洁**: 只保留最常用的功能，去除复杂的类结构
2. **高效**: 直接使用 Opik 原生 API，减少抽象层
3. **易用**: 装饰器模式，一行代码即可启用追踪
4. **稳定**: 异常处理完善，不会影响主业务逻辑
5. **灵活**: 支持自定义追踪名称和数据集管理

## 最佳实践

1. **在应用启动时调用 `configure()`**
2. **为重要的 LLM 调用添加 `@track_llm_call()` 装饰器**
3. **使用有意义的追踪名称来区分不同的功能模块**
4. **定期创建评估数据集来监控模型性能**
5. **在生产环境中确保 Opik 配置正确**

这个重写版本大大简化了原始代码，专注于核心功能，让开发者能够快速集成 Opik 监控功能。
