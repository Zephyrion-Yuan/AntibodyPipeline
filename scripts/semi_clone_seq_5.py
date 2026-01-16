import pandas as pd
import os
from typing import List, Dict, Any, Optional
import tkinter as tk
from tkinter import filedialog, messagebox


def read_excel_table(file_path: str) -> List[List[Any]]:
    """
    从Excel读取指定区域的数据并转换为8x12的列表
    """
    # 读取Excel文件的B2:M9区域（0-based索引对应1:9行和1:13列）
    df = pd.read_excel(file_path, header=None, skiprows=1, nrows=8, usecols="B:M")
    # 将缺失值填充为''
    df = df.fillna('')
    # 转换为二维列表
    return df.values.tolist()


def rearrange_table(original_table):
    if len(original_table) != 8 or any(len(row) != 12 for row in original_table):
        raise ValueError("输入表格必须是8行12列的列表")
    
    result = []

    for table_cnt in range(6):
        new_table = [ [0 for _ in range(4)] for _ in range(4)]
        base = table_cnt * 16
        for i in range(len(new_table)):
            for j in range(len(new_table[0])):
                index_r = (base + j * 4 + i) % 8
                index_c = (base + j * 4 + i) // 8
                new_table[i][j] = original_table[index_r][index_c]
        result.append(new_table)
    
    return result


def write_to_excel_sheets(tables: List[List[List[Any]]], output_dir: str) -> None:
    """每个4x4表格写到单独sheet，含表名、行列标题"""
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "plates_16_cells.xlsx")

    column_headers = ['1', '2', '3', '4']
    row_headers = ['A', 'B', 'C', 'D']

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for idx, table in enumerate(tables):
            cleaned_table = [[cell if cell != 'NA' else '' for cell in row] for row in table]
            df = pd.DataFrame(cleaned_table, columns=column_headers, index=row_headers)
            df.insert(0, '', df.index)
            # title_row = pd.DataFrame([[f'plate{idx+1}'] + [''] * (len(df.columns) - 1)], columns=df.columns)
            header_row = pd.DataFrame([df.columns], columns=df.columns)
            # full_table = pd.concat([title_row, header_row, df], ignore_index=True)
            full_table = pd.concat([header_row, df], ignore_index=True)
            full_table.to_excel(writer, sheet_name=f'plate{idx+1}', index=False, header=False)

    print(f"所有表格已分别保存为sheet至: {output_file}")


def expand_and_generate_boards(tables: List[List[List[Any]]]) -> List[List[List[str]]]:
    """
    将每个4x4表格元素扩展为带有-1至-5后缀的80个元素，并以行优先填入8x12板中。
    返回多个8x12板。
    """
    boards = []

    for table_idx, table in enumerate(tables):
        # flat_list = []
        # padding_list = []

        # for row in table:
        #     for cell in row:
        #         for i in range(1, 6):
        #             if cell:
        #                 flat_list.append(f"{cell}-{i}")
        #             else:
        #                 padding_list.append("")
        
        # flat_list.extend(padding_list)

        flat_list = []

        for row in table:
            for cell in row:
                for i in range(1, 6):
                    if cell:
                        flat_list.append(f"{cell}-{i}")
                    else:
                        flat_list.append("")
        
        if len(flat_list) != 80:
            raise ValueError(f"第 {table_idx+1} 个表格扩展后长度不是64，实际为 {len(flat_list)}")
        

        board = [flat_list[i * 10: (i + 1) * 10] + ['', ''] for i in range(8)]
        board = [flat_list[i * 10: (i * 10 + 5)] + [''] + flat_list[(i * 10 + 5): (i + 1) * 10] + [''] for i in range(8)]
        boards.append(board)

    return boards


def write_expanded_boards_to_excel_sheets(boards: List[List[List[str]]], output_dir: str) -> None:
    """
    将多个8x12板分别写入同一个Excel文件，不同sheet。
    每个sheet带列标题（1~12）和行索引（A~H），sheet名为送测板1, 送测板2等。
    """
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "plates_sequencing.xlsx")

    column_headers = [str(i) for i in range(1, 13)]
    row_headers = list("ABCDEFGH")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for idx, board in enumerate(boards):
            cleaned_boards = [[cell if cell != 'NA' else '' for cell in row] for row in board]
            df = pd.DataFrame(cleaned_boards, columns=column_headers, index=row_headers)
            # 行名作为第一列
            df.insert(0, '', df.index)
            # # 标题行：送测板-1
            # title_row = pd.DataFrame([[f'送测板{idx+1}'] + [''] * (len(df.columns) - 1)], columns=df.columns)
            # 列标题行
            header_row = pd.DataFrame([df.columns], columns=df.columns)
            # 合并
            # full_table = pd.concat([title_row, header_row, df], ignore_index=True)
            full_table = pd.concat([header_row, df], ignore_index=True)
            # 写入单独sheet
            full_table.to_excel(writer, sheet_name=f'{idx+1}', index=False, header=False)

    print(f"所有8x12板已分别保存为sheet至: {output_file}")


def select_input_file() -> Optional[str]:
    """打开文件选择对话框并返回选择的文件路径"""
    root = tk.Toplevel()
    root.withdraw()  # 隐藏主窗口
    file_path = filedialog.askopenfilename(
        title="选择Excel文件",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    return file_path if file_path else None

def get_output_directory(input_file: str) -> str:
    """根据输入文件路径确定输出目录"""
    input_dir = os.path.dirname(os.path.abspath(input_file))
    file_name = os.path.splitext(os.path.basename(input_file))[0]
    return os.path.join(input_dir, f"{file_name}_output")


def main():
    try:
        # 选择输入文件
        input_file = select_input_file()
        if not input_file:
            print("未选择文件，程序退出")
            return
            
        # 读取Excel文件
        original_table = read_excel_table(input_file)
        
        # 执行重排
        rearranged_tables = rearrange_table(original_table)
        
        # 确定输出目录（与输入文件同目录下的子文件夹）
        output_dir = get_output_directory(input_file)
        
        # 写入Excel文件
        write_to_excel_sheets(rearranged_tables, output_dir)

        # 生成多个8x12板
        expanded_boards = expand_and_generate_boards(rearranged_tables)

        # 输出为Excel
        write_expanded_boards_to_excel_sheets(expanded_boards, output_dir)

        
        # 显示成功消息
        messagebox.showinfo(
            "完成", 
            f"表格重排完成！\n保存路径: {output_dir}"
        )
        print(f"表格重排完成！输出目录: {output_dir}")
        
    except Exception as e:
        messagebox.showerror("错误", f"发生错误: {str(e)}")
        print(f"发生错误: {e}")    
    
    return


if __name__ == "__main__":
    main()
