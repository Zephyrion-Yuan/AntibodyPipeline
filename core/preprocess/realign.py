import pandas as pd
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import os

def reshape_excel(input_file, output_file):
    """
    将Excel文件中的96×1数据重排为8×12格式
    
    参数:
    input_file (str): 输入Excel文件路径
    output_file (str): 输出Excel文件路径
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(input_file, header=None)
        
        # 提取数据为一维数组
        data = df[0].tolist()

        # 检查数据是否符合96×1的格式
        # 计算需要填充的数量
        padding_needed = 96 - len(data)
        
        # 用空字符串填充不足的部分
        if padding_needed > 0:
            data.extend([""] * padding_needed)
        
        # 按列优先重排数据
        # 将96个元素按列优先填充到8行12列的矩阵中
        reshaped_data = pd.Series(data).values.reshape(8, 12, order='F')
        
        # 创建新的DataFrame
        reshaped_df = pd.DataFrame(reshaped_data)
        
        # 保存为Excel文件
        reshaped_df.to_excel(output_file, index=False, header=False)
        
        print(f"数据已成功重排并保存到 {output_file}")
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        sys.exit(1)


def main():
    root = tk.Toplevel()
    root.withdraw()
    xlsx_path = filedialog.askopenfilename(title="选择含一列96行数据的xlsx", filetypes=[("Excel files", "*.xlsx")])
    output_dir = os.path.dirname(xlsx_path)
    output_file = os.path.join(output_dir, f"plate.xlsx")
    reshape_excel(xlsx_path, output_file)

if __name__ == "__main__":
    main()