from typing import Optional
from tkinter import filedialog
import tkinter as tk
import os
from tkinter import messagebox

def analyze_samples(input_file, output_file):
    # 存储每个样本组及其包含的编号
    sample_groups = {}

    # 获取输入文件的目录
    input_dir = os.path.dirname(input_file)
    # 构建输出文件的完整路径（与输入文件同目录）
    output_file = os.path.join(input_dir, output_file)
    
    
    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # # 分割样本名，获取基础部分和编号
            base_name = line.split('-')[0]

            # 最后的编号（转换为整数）
            try:
                number = line.split('-')[-1]
            except ValueError:
                continue  # 跳过编号不是数字的行
            
            # 将编号添加到对应的样本组
            if base_name not in sample_groups:
                sample_groups[base_name] = set()
            sample_groups[base_name].add(int(number))
    
    # 找出包含1-5所有编号的样本组
    complete_groups = []
    required_numbers = {1, 2, 3, 4, 5}
    for base_name, numbers in sample_groups.items():
        if required_numbers.issubset(numbers):
            complete_groups.append(base_name)
    
    # 输出结果到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for group in complete_groups:
            f.write(f"{group}\n")
    
    print(f"分析完成，共找到 {len(complete_groups)} 个完整样本组")
    print(f"结果已保存到 {output_file}")


def select_input_file() -> Optional[str]:
    """打开文件选择对话框并返回选择的文件路径"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    file_path = filedialog.askopenfilename(
        title="选择Txt文件，第一列为单克隆名",
        filetypes=[("txt files", "*.txt")]
    )
    return file_path if file_path else None


def main():
    """主函数，调用其他函数"""
    input_file = select_input_file()
    if input_file:
        output_file = "nomatch_samples.txt"
        analyze_samples(input_file, output_file)
    else:
        messagebox.showwarning("已取消", "未选择文件。")
        return

# 使用示例
if __name__ == "__main__":
    main()
