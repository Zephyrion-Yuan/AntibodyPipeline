import tkinter as tk
from tkinter import ttk
import sys
import os

# def run_gen_seq():
#     from scripts import gen_seq_auto_detect_lc_classify
#     gen_seq_auto_detect_lc_classify.main()

def run_gen_seq():
    from scripts import gen_seq_auto_detect_chain_classify_report
    gen_seq_auto_detect_chain_classify_report.main()

def run_receive_arm_conc_norm():
    from scripts import receive_arm_conc_norm
    receive_arm_conc_norm.main()

def run_semi_clone_seq():
    from scripts import semi_clone_seq_5
    semi_clone_seq_5.main()

def run_plasmid_seq_align():
    from scripts import plasmid_seq_align
    plasmid_seq_align.main()

def run_germ_cherry_transfer():
    from scripts import germ_cherry_transfer
    germ_cherry_transfer.main()

def run_plasmid_conc():
    from scripts import plasmid_conc
    plasmid_conc.main()

def run_plasmid_mix():
    from scripts import plasmid_mix
    plasmid_mix.main()

def run_conc_norm():
    from scripts import conc_norm
    conc_norm.main()

def run_plasmid_save_cherry_transfer():
    from scripts import plasmid_save_cherry_transfer
    plasmid_save_cherry_transfer.main()

def run_xlsx2fasta():
    from scripts import xlsx2fasta
    xlsx2fasta.main()

def run_xlsxrealign():
    from scripts import xlsxrealign
    xlsxrealign.main()

def run_find_no_matches():
    from scripts import find_no_matches
    find_no_matches.main()

def run_replace_correct_clones():
    from scripts import replace_correct_clones
    replace_correct_clones.main()

def run_query_samples_and_highlights():
    from scripts import query_samples_and_highlights
    query_samples_and_highlights.main()


def run_translate_to_AA():
    from scripts import translate_to_AA
    translate_to_AA.main()

def separate_primer_synthesis_tables():
    from scripts import separate_primer_synthesis_tables
    separate_primer_synthesis_tables.main()

def move_files():
    from scripts import move_files
    move_files.main()

SCRIPTS = [
    ("gen_seq.py", run_gen_seq, "翻译优化密码子&加同源臂"),
    ("receive_plas_conc_norm.py", run_receive_arm_conc_norm, "根据片段浓度均一化"),
    ("semi_clone_seq.py", run_semi_clone_seq, "生成涂板&挑单克隆&送测的布局表"),
    ("plasmid_seq_align.py", run_plasmid_seq_align, "质粒测序结果自动比对"),
    ("replace_correct_clones.py", run_replace_correct_clones, "替换正确的单克隆布局"),
    ("germ_cherry_transfer.py", run_germ_cherry_transfer, "转移&排序比对正确的样本菌液"),
    ("plasmid_save_cherry_transfer.py", run_plasmid_save_cherry_transfer, "保存比对正确的返测质粒"),
    ("plasmid_conc.py", run_plasmid_conc, "根据Qbit计算96孔质粒的浓度"),
    ("plasmid_mix.py", run_plasmid_mix, "匹配重链质粒&轻链质粒并转染"),
    ("conc_norm.py", run_conc_norm, "根据BCA计算抗体浓度并均一化"),
    ("xlsx2fasta.py", run_xlsx2fasta, "将xlsx格式核酸序列转为fasta"),
    ("separate_primer_synthesis_tables.py", separate_primer_synthesis_tables, "分离合成引物返样表"),
    ("query_samples_and_highlights.py", run_query_samples_and_highlights, "查询并高亮样本"),
    ("xlsxrealign.py", run_xlsxrealign, "将xlsx的96*1数据转为布局表"),
    ("translate_to_AA.py", run_translate_to_AA, "将序列翻译为氨基酸"),
    ("move_files.py", move_files, "移动子目录所有文件到母目录"),
]


def get_resource_path(filename):
    """
    保证无论PyInstaller打包还是源码调试，均返回main.exe或main.py同目录下文件的绝对路径
    """
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

def on_enter(e):
    e.widget.configure(style='Hover.TButton')

def on_leave(e):
    e.widget.configure(style='TButton')
def main():
    root_main = tk.Tk()
    root_main.title("AI自动化抗体工具箱")
    root_main.geometry("+400+150")
    root_main.resizable(False, False)

    # 设置窗口图标（可选，有icon.ico就启用）
    icon_path = get_resource_path("icon.ico")
    if os.path.exists(icon_path):
        root_main.iconbitmap(icon_path)

    # 主题美化
    root_main.configure(bg='white')
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('TFrame', background='#ffffff')
    style.configure('TButton', font=('微软雅黑', 10), padding=6, background='#ffffff')
    style.configure('Hover.TButton', font=('微软雅黑', 10), padding=6, background='#edf7ff')
    style.configure('Title.TLabel', font=('微软雅黑', 16, 'bold'), foreground='#175CA4', padding=8, background='#ffffff')
    style.configure('Desc.TLabel', font=('微软雅黑', 9), foreground='#333333', padding=4, background='#ffffff')

    # 顶部标题
    ttk.Label(root_main, text="分子实验自动化工具箱", style='Title.TLabel').pack(pady=(12, 2))

    sep = ttk.Separator(root_main, orient='horizontal')
    sep.pack(fill='x', padx=15, pady=3)

    # 创建一个2列的网格布局
    frm = ttk.Frame(root_main)
    frm.pack(padx=15, pady=5, fill='both', expand=True)
    
    # 设置列权重，使两列平均分布空间
    frm.columnconfigure(0, weight=1)
    frm.columnconfigure(1, weight=1)

    # 计算需要的行数
    total_scripts = len(SCRIPTS)
    rows_needed = (total_scripts + 1) // 2  # 向上取整

    # 使用网格布局，分两列显示按钮
    for i, (_, func, desc) in enumerate(SCRIPTS):
        row = i // 2
        col = i % 2
        
        script_frame = ttk.Frame(frm)
        script_frame.grid(row=row, column=col, padx=(0, 10) if col == 0 else (10, 0), pady=5, sticky='ew')
        
        btn = ttk.Button(script_frame, text=f"▶ start", width=16, command=func)
        btn.pack(side='left', padx=(0, 8))
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        ttk.Label(script_frame, text=desc, style='Desc.TLabel', anchor='w', wraplength=220, justify='left').pack(side='left', fill='x', expand=True)

    # 底部提示
    ttk.Label(root_main, text="© 2025 MEGAROBO 鲲鹏实验室 | v1.1 | written by YHZ", font=('微软雅黑', 8), foreground="#8b8b8b").pack(pady=8)

    root_main.mainloop()
    sys.exit(0)
    
if __name__ == '__main__':
    main()

# python -m PyInstaller --onefile main.py --noconsole --hidden-import=generate_seq -n AntibodyToolbox.v1.4 --icon=icon.ico --add-data "d:\Desktop\AI抗体\.venv\Lib\site-packages\dnachisel\biotools\data;dnachisel/biotools/data" --add-data "d:\Desktop\AI抗体\.venv\Lib\site-packages\python_codon_tables\codon_usage_data\tables;python_codon_tables/codon_usage_data/tables"
