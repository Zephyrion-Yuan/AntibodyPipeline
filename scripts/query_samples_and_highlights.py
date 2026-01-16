import os
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from openpyxl.utils.exceptions import InvalidFileException
from core.ui_inputs import UIContext

def normalize_sample(value):
    """标准化样本值，去除空白并统一字符串格式。"""
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def read_samples(txt_file):
    """从txt文件中读取样本，每行一个样本。"""
    try:
        with open(txt_file, 'r', encoding='utf-8') as f:
            # 使用集合去重并加速后续匹配
            samples = {
                normalized
                for line in f
                if (normalized := normalize_sample(line))
            }
        return samples
    except Exception as e:
        print(f"读取TXT文件时出错: {str(e)}")
        return None

def highlight_matches(xlsx_file, samples):
    """在xlsx文件中高亮匹配的样本。"""
    try:
        # 加载工作簿
        wb = load_workbook(xlsx_file)

        # 创建黄色填充样式
        yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
        
        # 遍历所有工作表
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            print(f"正在处理工作表: {sheet_name}")

            # 遍历所有单元格，使用集合加速匹配
            for row in sheet.iter_rows():
                for cell in row:
                    cell_value = normalize_sample(cell.value)
                    if cell_value and cell_value in samples:
                        print(cell_value)
                        cell.fill = yellow_fill
        
        # 生成输出文件名和路径
        xlsx_dir = os.path.dirname(xlsx_file)
        xlsx_name = os.path.basename(xlsx_file)
        output_file = os.path.join(xlsx_dir, f"highlighted_{xlsx_name}")
        
        # 保存高亮后的文件
        wb.save(output_file)
        return output_file
        
    except InvalidFileException:
        print("选择的文件不是有效的XLSX文件")
        return None
    except Exception as e:
        print(f"处理XLSX文件时出错: {str(e)}")
        return None

def main():
    ui = UIContext.from_env()
    txt_file = ui.require_input("txt_file")
    xlsx_file = ui.require_input("xlsx_file")
        
    # 读取样本
    samples = read_samples(txt_file)
    if not samples:
        ui.warn("未从TXT文件中读取到任何样本")
        return

    print(f"已读取 {len(samples)} 个样本")
    
    # 高亮匹配
    output_file = highlight_matches(xlsx_file, samples)
    
    if output_file:
        ui.info(f"处理完成！文件已保存至: {output_file}")
    else:
        ui.error("处理过程中出现错误，未能生成输出文件")

if __name__ == "__main__":
    main()
