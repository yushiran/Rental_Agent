# RentalLatex 使用说明

`RentalLatex` 是一个用于生成租赁协议 PDF 的 Python 类，让用户只需要输入自定义内容就可以生成专业的 PDF 租赁合同。

## 功能特点

- 基于 LaTeX 模板生成高质量 PDF
- 支持自定义所有租赁协议参数
- 提供多种使用方式（类、数据类、字典）
- 包含实用的日期和货币格式化函数
- 自动处理 LaTeX 编译过程

## 安装要求

确保系统已安装：
- Python 3.7+
- LaTeX 发行版（texlive、XeLaTeX 或 pdflatex）

## 快速开始

### 1. 基本使用（字典方式）

```python
from app.latex.rental_latex import generate_rental_pdf

# 定义租赁信息
rental_data = {
    'agreement_date': '28/05/2025',
    'landlord_name': 'John Smith',
    'tenant_name': 'Alice Johnson',
    'property_address': '123 Main Street, London SW1A 1AA',
    'monthly_rent': '£1200',
    'security_deposit': '£1200',
    'start_date': '01/06/2025',
    'tenancy_end_date': '31/05/2026',
    'tenancy_duration': '12 months'
}

# 生成 PDF
output_path = "rental_agreement.pdf"
generate_rental_pdf(rental_data, output_path)
print(f"PDF 已生成：{output_path}")
```

### 2. 使用类的方式

```python
from app.latex.rental_latex import RentalLatex

# 创建生成器实例
generator = RentalLatex()

# 从字典生成 PDF
rental_data = {...}  # 同上
result_path = generator.generate_pdf_from_dict(rental_data, "output.pdf")
```

### 3. 使用数据类

```python
from app.latex.rental_latex import RentalLatex, RentalInfo

# 创建租赁信息对象
rental_info = RentalInfo(
    agreement_date="28/05/2025",
    landlord_name="Jane Doe",
    tenant_name="Bob Wilson",
    property_address="456 Oak Avenue, Manchester M1 1AA",
    monthly_rent="£950",
    security_deposit="£950",
    start_date="15/06/2025",
    tenancy_end_date="14/06/2026",
    tenancy_duration="12 months"
)

# 生成 PDF
generator = RentalLatex()
result_path = generator.generate_pdf(rental_info, "agreement.pdf")
```

### 4. 使用工具函数

```python
from app.latex.rental_latex import RentalLatex
from datetime import datetime

# 日期格式化
date_obj = datetime(2025, 5, 28)
formatted_date = RentalLatex.format_date(date_obj)  # "28/05/2025"

# 货币格式化
amount = 1250.0
formatted_amount = RentalLatex.format_currency(amount)  # "£1250"
```

## 可自定义的参数

所有以下参数都可以自定义，如果不提供将使用模板默认值：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `agreement_date` | 协议签署日期 | 空白线 |
| `landlord_name` | 房东姓名 | "Yu" |
| `tenant_name` | 租客姓名 | "Shiran" |
| `property_address` | 房产地址 | "Stapleton House, B607G N7 8FB" |
| `monthly_rent` | 月租金 | "£150" |
| `security_deposit` | 押金 | "£100" |
| `start_date` | 租赁开始日期 | "01/05/2025" |
| `tenancy_end_date` | 租赁结束日期 | "01/06/2025" |
| `tenancy_duration` | 租赁期限 | "1 month" |

## 错误处理

类会自动处理以下情况：
- 模板文件不存在
- LaTeX 编译错误（会尝试不同的编译器）
- 输出目录不存在（自动创建）
- 部分数据缺失（使用默认值）

## 高级用法

### 使用自定义模板

```python
from app.latex.rental_latex import RentalLatex

# 使用自定义模板路径
custom_template = "/path/to/custom/template.tex"
generator = RentalLatex(template_path=custom_template)
```

### 批量生成

```python
from app.latex.rental_latex import RentalLatex

generator = RentalLatex()

# 租客列表
tenants = [
    {"tenant_name": "Alice", "monthly_rent": "£800"},
    {"tenant_name": "Bob", "monthly_rent": "£900"},
    {"tenant_name": "Charlie", "monthly_rent": "£750"}
]

# 批量生成
for i, tenant_data in enumerate(tenants):
    output_file = f"agreement_{i+1}.pdf"
    generator.generate_pdf_from_dict(tenant_data, output_file)
    print(f"生成了 {output_file}")
```

## 技术细节

- 支持 XeLaTeX 和 pdflatex 编译器
- 使用临时目录进行编译，避免污染工作目录
- 自动进行两次编译以确保交叉引用正确
- 支持 Unicode 字符（通过 XeLaTeX）

## 故障排除

1. **LaTeX 未安装**：确保系统已安装 texlive 或类似发行版
2. **编译失败**：检查模板语法是否正确
3. **权限问题**：确保有写入输出目录的权限
4. **模板不存在**：检查模板文件路径是否正确

## 示例输出

生成的 PDF 包含：
- 标准的英国租赁协议格式
- 所有必要的法律条款
- 签名区域
- 专业的排版和格式
