#!/usr/bin/env python3
"""
PDF to Side-by-Side Image Converter
将两页PDF转换为并排展示的单张图片，用于论文插图

Usage:
    python pdf_to_side_by_side_image.py <input_pdf> [output_image]

Dependencies:
    pip install PyMuPDF Pillow
"""

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import sys
import os
import io
from pathlib import Path
import argparse


def pdf_to_side_by_side_image(
    pdf_path: str,
    output_path: str = None,
    dpi: int = 300,
    spacing: int = 20,
    add_page_numbers: bool = True,
    background_color: str = "white"
) -> str:
    """
    将PDF的前两页转换为并排展示的图片
    
    Args:
        pdf_path: PDF文件路径
        output_path: 输出图片路径，如果为None则自动生成
        dpi: 图片分辨率
        spacing: 两页之间的间距（像素）
        add_page_numbers: 是否添加页码标注
        background_color: 背景颜色
        
    Returns:
        str: 输出图片的路径
    """
    
    # 检查输入文件是否存在
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    # 生成输出路径
    if output_path is None:
        pdf_stem = Path(pdf_path).stem
        output_dir = Path(pdf_path).parent
        output_path = output_dir / f"{pdf_stem}_side_by_side.png"
    
    print(f"正在处理PDF: {pdf_path}")
    print(f"输出路径: {output_path}")
    
    # 打开PDF文档
    doc = fitz.open(pdf_path)
    
    if len(doc) < 2:
        print("警告: PDF少于2页，将只显示第一页")
        pages_to_convert = [0]
    else:
        pages_to_convert = [0, 1]  # 前两页
    
    # 转换页面为图片
    page_images = []
    for page_num in pages_to_convert:
        page = doc[page_num]
        
        # 设置缩放矩阵以获得指定DPI
        zoom = dpi / 72.0  # PDF默认72 DPI
        mat = fitz.Matrix(zoom, zoom)
        
        # 渲染页面为图片
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # 转换为PIL Image
        img = Image.open(io.BytesIO(img_data))
        page_images.append(img)
        print(f"已转换第 {page_num + 1} 页，尺寸: {img.size}")
    
    doc.close()
    
    # 如果只有一页，直接保存
    if len(page_images) == 1:
        page_images[0].save(output_path, "PNG", dpi=(dpi, dpi))
        print(f"单页图片已保存: {output_path}")
        return str(output_path)
    
    # 计算合并后的图片尺寸
    page1, page2 = page_images
    
    # 统一两页的高度（使用较大的高度）
    max_height = max(page1.height, page2.height)
    
    # 如果高度不同，重新调整图片大小
    if page1.height != max_height:
        ratio = max_height / page1.height
        new_width = int(page1.width * ratio)
        page1 = page1.resize((new_width, max_height), Image.Resampling.LANCZOS)
    
    if page2.height != max_height:
        ratio = max_height / page2.height
        new_width = int(page2.width * ratio)
        page2 = page2.resize((new_width, max_height), Image.Resampling.LANCZOS)
    
    # 创建合并后的图片
    total_width = page1.width + page2.width + spacing
    combined_img = Image.new("RGB", (total_width, max_height), background_color)
    
    # 粘贴两页
    combined_img.paste(page1, (0, 0))
    combined_img.paste(page2, (page1.width + spacing, 0))
    
    # 添加页码标注（可选）
    if add_page_numbers:
        draw = ImageDraw.Draw(combined_img)
        
        # 尝试使用系统字体，如果失败则使用默认字体
        try:
            # 字体大小根据DPI调整
            font_size = max(20, int(dpi / 15))
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
        
        # 添加页码
        page1_text = "Page 1"
        page2_text = "Page 2"
        
        if font:
            # 在页面底部中央添加页码
            page1_bbox = draw.textbbox((0, 0), page1_text, font=font)
            page1_text_width = page1_bbox[2] - page1_bbox[0]
            page1_x = (page1.width - page1_text_width) // 2
            page1_y = max_height - 40
            
            page2_bbox = draw.textbbox((0, 0), page2_text, font=font)
            page2_text_width = page2_bbox[2] - page2_bbox[0]
            page2_x = page1.width + spacing + (page2.width - page2_text_width) // 2
            page2_y = max_height - 40
            
            # 添加白色背景
            margin = 5
            draw.rectangle([page1_x - margin, page1_y - margin, 
                          page1_x + page1_text_width + margin, page1_y + 25 + margin], 
                         fill="white", outline="black")
            draw.rectangle([page2_x - margin, page2_y - margin, 
                          page2_x + page2_text_width + margin, page2_y + 25 + margin], 
                         fill="white", outline="black")
            
            # 绘制文字
            draw.text((page1_x, page1_y), page1_text, fill="black", font=font)
            draw.text((page2_x, page2_y), page2_text, fill="black", font=font)
    
    # 保存合并后的图片
    combined_img.save(output_path, "PNG", dpi=(dpi, dpi))
    
    print(f"并排图片已保存: {output_path}")
    print(f"图片尺寸: {combined_img.size}")
    print(f"分辨率: {dpi} DPI")
    
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="将PDF的前两页转换为并排展示的图片")
    parser.add_argument("pdf_path", help="输入PDF文件路径")
    parser.add_argument("-o", "--output", help="输出图片路径")
    parser.add_argument("--dpi", type=int, default=300, help="图片分辨率 (默认: 300)")
    parser.add_argument("--spacing", type=int, default=20, help="两页间距离像素 (默认: 20)")
    parser.add_argument("--no-page-numbers", action="store_true", help="不添加页码标注")
    parser.add_argument("--background", default="white", help="背景颜色 (默认: white)")
    
    args = parser.parse_args()
    
    try:
        output_path = pdf_to_side_by_side_image(
            pdf_path=args.pdf_path,
            output_path=args.output,
            dpi=args.dpi,
            spacing=args.spacing,
            add_page_numbers=not args.no_page_numbers,
            background_color=args.background
        )
        
        print("\n✅ 转换完成！")
        print(f"输出文件: {output_path}")
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 如果没有参数，使用demo文件
        demo_pdf = "/home/yushiran/rental_agent2/Rental_Agent/backend/workspace/latex/demo/basic_rental_agreement.pdf"
        if os.path.exists(demo_pdf):
            print("未提供参数，使用demo文件...")
            output_path = pdf_to_side_by_side_image(demo_pdf)
            print("\n✅ Demo转换完成！")
            print(f"输出文件: {output_path}")
        else:
            print("请提供PDF文件路径作为参数")
            print("用法: python pdf_to_side_by_side_image.py <pdf_path> [output_path]")
    else:
        main()
