import pandas as pd
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path


def reshape_excel(input_file):
    """
    将Excel文件中的96×1数据重排为8×12格式
    
    参数:
    input_file (str): 输入Excel文件路径
    """
    try:
        file_path = Path(input_file)
        plate_name = file_path.stem
        output_file = file_path.with_stem(f"{plate_name}_output")
        # 读取Excel文件
        df = pd.read_excel(input_file, header=None)

        column_headers = [str(i) for i in range(1, 13)]
        row_headers = list("ABCDEFGH")
        
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
        reshaped_df = pd.DataFrame(reshaped_data, columns=column_headers, index=row_headers)
        reshaped_df.insert(0, '', reshaped_df.index)
        
        header_row = pd.DataFrame([reshaped_df.columns], columns=reshaped_df.columns)
        # 合并
        full_table = pd.concat([header_row, reshaped_df], ignore_index=True)
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # 写入单独sheet
            full_table.to_excel(writer, sheet_name=f'{plate_name}', index=False, header=False)

        print(f"数据已成功重排并保存到 {output_file}")
        messagebox.showinfo(
            "完成", 
            f"表格重排完成！\n保存路径: {output_file}"
        )
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        sys.exit(1)


def main():
    root = tk.Toplevel()
    root.withdraw()
    xlsx_path = filedialog.askopenfilename(title="选择含一列96行数据的xlsx", filetypes=[("Excel files", "*.xlsx")])
    if not xlsx_path:
        messagebox.showwarning("已取消", "未选择文件。")
        return
    reshape_excel(xlsx_path)

if __name__ == "__main__":
    main()