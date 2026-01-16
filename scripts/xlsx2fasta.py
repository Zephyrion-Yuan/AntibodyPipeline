import pandas as pd
import tkinter as tk
import tkinter.filedialog as filedialog
from typing import Optional
from tkinter import messagebox
from pathlib import PurePath, Path


def select_input_file() -> Optional[str]:
    """打开文件选择对话框并返回选择的文件路径"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    file_path = filedialog.askopenfilename(
        title="选择Excel文件，表头依次为名称、核苷酸序列",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    return file_path if file_path else None


def main():
    # 选择输入文件
    input_file = select_input_file()
    if not input_file:
        messagebox.showwarning("已取消", "未选择文件。")
        return
    try:
        input = pd.read_excel(input_file)
    except Exception:
        raise ValueError("无法读取输入文件，检查是否为xlsx文件")
    
    
    input_path = Path(input_file)
    # input_name = PurePath(input_file).stem
    
    fasta_list = []
    for index, row in input.iterrows():
        name = row["名称"]
        nt_seq = row["核苷酸序列"]
        fasta_list.append(f'>{name}\n')
        for i in range(0, len(nt_seq), 60):
                fasta_list.append(nt_seq[i:i+60] + '\n')
    fasta_wirte = ''.join(fasta_list)


    # 使用 pathlib.Path 处理路径
    # output_fasta = ''.join([str(input_path.parent), f"/{input_path.stem}_output.fasta"])
    output_fasta = input_path.with_name(f"{input_path.stem}_output.fasta")
    with open (output_fasta, 'w') as f:
        f.write(fasta_wirte)

    print('Done!')
    result_msg = (
        f"处理完成！\n\n"
        f"参考序列: {input_path.stem}_output.fasta \n"
    )

    messagebox.showinfo("完成", result_msg)

if __name__ == '__main__':
    main()