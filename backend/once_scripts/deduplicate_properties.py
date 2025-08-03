#!/usr/bin/env python3
"""
去重脚本：处理rightmove_data_processed.json中的重复property_id
只保留每个property_id的第一个对象
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from loguru import logger

def deduplicate_properties(input_file: str, output_file: str = None) -> None:
    """
    去除重复的property_id，只保留每个property_id的第一个对象
    
    Args:
        input_file: 输入JSON文件路径
        output_file: 输出JSON文件路径，如果为None则覆盖原文件
    """
    
    # 读取原始数据
    logger.info(f"正在读取文件: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"文件不存在: {input_file}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}")
        return
    
    if not isinstance(data, list):
        logger.error("数据格式错误：期望是一个列表")
        return
    
    logger.info(f"原始数据包含 {len(data)} 个对象")
    
    # 使用字典来去重，key是property_id，value是第一个遇到的对象
    seen_property_ids: Dict[Any, Dict] = {}
    duplicate_count = 0
    
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning(f"索引 {i} 的对象不是字典类型，跳过")
            continue
            
        property_id = item.get('property_id')
        
        if property_id is None:
            logger.warning(f"索引 {i} 的对象没有property_id字段，跳过")
            continue
        
        if property_id in seen_property_ids:
            duplicate_count += 1
            logger.debug(f"发现重复的property_id: {property_id} (索引 {i})")
        else:
            seen_property_ids[property_id] = item
    
    # 转换回列表
    deduplicated_data = list(seen_property_ids.values())
    
    logger.info("去重完成:")
    logger.info(f"  - 原始对象数量: {len(data)}")
    logger.info(f"  - 重复对象数量: {duplicate_count}")
    logger.info(f"  - 去重后对象数量: {len(deduplicated_data)}")
    logger.info(f"  - 唯一property_id数量: {len(seen_property_ids)}")
    
    # 确定输出文件路径
    if output_file is None:
        output_file = input_file
        # 创建备份
        backup_file = f"{input_file}.backup"
        logger.info(f"创建备份文件: {backup_file}")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 写入去重后的数据
    logger.info(f"正在写入去重后的数据到: {output_file}")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(deduplicated_data, f, ensure_ascii=False, indent=2)
        logger.success(f"去重完成，结果已保存到: {output_file}")
    except Exception as e:
        logger.error(f"写入文件失败: {e}")

def analyze_duplicates(input_file: str) -> None:
    """
    分析重复的property_id，显示详细统计信息
    
    Args:
        input_file: 输入JSON文件路径
    """
    logger.info(f"正在分析重复数据: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        return
    
    if not isinstance(data, list):
        logger.error("数据格式错误：期望是一个列表")
        return
    
    # 统计每个property_id的出现次数
    property_id_counts: Dict[Any, int] = {}
    property_id_indexes: Dict[Any, List[int]] = {}
    
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
            
        property_id = item.get('property_id')
        if property_id is None:
            continue
        
        property_id_counts[property_id] = property_id_counts.get(property_id, 0) + 1
        if property_id not in property_id_indexes:
            property_id_indexes[property_id] = []
        property_id_indexes[property_id].append(i)
    
    # 找出重复的property_id
    duplicates = {pid: count for pid, count in property_id_counts.items() if count > 1}
    
    logger.info("数据分析结果:")
    logger.info(f"  - 总对象数量: {len(data)}")
    logger.info(f"  - 唯一property_id数量: {len(property_id_counts)}")
    logger.info(f"  - 重复的property_id数量: {len(duplicates)}")
    
    if duplicates:
        logger.info("重复的property_id详情:")
        for pid, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:10]:
            indexes = property_id_indexes[pid]
            logger.info(f"  - property_id {pid}: 出现 {count} 次，索引位置: {indexes}")

def main():
    """主函数"""
    # 设置数据文件路径
    base_path = Path(__file__).parent.parent
    input_file = base_path / "dataset" / "rent_cast_data" / "processed" / "rightmove_data_processed.json"
    
    if not input_file.exists():
        logger.error(f"输入文件不存在: {input_file}")
        return
    
    # 分析重复数据
    logger.info("=" * 50)
    logger.info("步骤 1: 分析重复数据")
    logger.info("=" * 50)
    analyze_duplicates(str(input_file))
    
    # 询问用户是否继续
    logger.info("=" * 50)
    logger.info("步骤 2: 执行去重操作")
    logger.info("=" * 50)
    
    try:
        response = input("是否继续执行去重操作？(y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            logger.info("用户取消操作")
            return
    except KeyboardInterrupt:
        logger.info("\n用户取消操作")
        return
    
    # 执行去重
    deduplicate_properties(str(input_file))
    
    # 再次分析验证结果
    logger.info("=" * 50)
    logger.info("步骤 3: 验证去重结果")
    logger.info("=" * 50)
    analyze_duplicates(str(input_file))

if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO"
    )
    
    main()
