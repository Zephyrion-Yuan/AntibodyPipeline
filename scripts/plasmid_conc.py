from core.struc_plates_96 import PlateWorkbook, PlateSheet
from core.read_config_path import get_app_dir, get_meipass_dir, find_config_path

import pandas as pd
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import os
from typing import Tuple
import configparser
from pathlib import Path

def natural_key(string):
    # 用tuple替代list, tuple可hash
    return tuple(int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(string)))

def std_curve(c: float, b: float, a: float, scale: float, input_value: float) -> float:
    """
    返回:
    float: 转换后的输出值，保留两位小数
    """
    # 计算标准曲线转换
    denominator = b * scale
    if denominator == 0:
        messagebox.showerror("错误", "b和scale不能为0")
        return
    factor = a / denominator
    
    # 规范化结果，保留两位小数（四舍五入）
    return round((input_value - c) * factor, 2)

def read_asc_column(file_path, sep='\t'):
    data = []
    try:
        with open(file_path, 'r', encoding='utf-16') as file:
            read_end = False
            for _ in range(96):
                if read_end:
                    data.append(0)
                else:
                    line = file.readline()
                    if not line:
                        break
                    # 分割行并提取第1列（索引0）
                    columns = line.strip().split(sep)
                    if columns:
                        first_col = columns[0]
                        # 检查第一个字符是否为数字
                        if first_col and first_col[0].isdigit():
                            data.append(first_col)
                        else:
                            read_end = True
                            data.append(0)
    except FileNotFoundError:
        print(f"错误：文件 '{file_path}' 不存在")
    except Exception as e:
        print(f"读取文件时发生错误: {e}")
    return data



def calculate_plasmid_conc(plate: PlateSheet, eli_reads: list, c:float, b:float, a:float, scale:float, m:float) -> Tuple[PlateWorkbook, pd.DataFrame]:
    """
    根据提供的plate文件和浓度文件，计算质粒浓度并生成结果
    
    参数:
    plate_path (str): 包含plate数据的Excel文件路径
    conc_path (str): 浓度标准曲线参数文件路径

    计算方式
    conc = (read - c) * a / (b * scale)
    volume = m / conc
    
    返回:
    Tuple[PlateWorkbook, pd.DataFrame]: 处理后的PlateWorkbook对象和输出DataFrame
    """
    df_conc = pd.DataFrame(eli_reads, columns=['Qbit'])

    # 使用 std_curve 函数计算 Adjusted concentration
    df_conc['Adjusted concentration'] = df_conc['Qbit'].apply(
        lambda x: std_curve(c, b, a, scale, float(x)) if x else None
    )

    # 添加抗体名称
    # df_conc['Plasmid'] = plate.data.iloc[1:,1:].values.flatten(order='F').tolist()

    n_rows = len(df_conc)
     # 关键修复：从plate中提取质粒名称，只取前n_rows个（与eli_reads长度匹配）
    all_plasmids = plate.data.iloc[1:, 1:].values.flatten(order='F').tolist()
    # 截取与df_conc行数一致的质粒名称（确保长度匹配）
    matched_plasmids = all_plasmids[:n_rows]
    # 若plate中的质粒数量不足（极端情况），用None填充
    if len(matched_plasmids) < n_rows:
        matched_plasmids += [None] * (n_rows - len(matched_plasmids))
    
    df_conc['Plasmid'] = matched_plasmids  # 此时长度一定匹配

    # 计算所需体积 v = m / adjusted concentration，并保留两位小数
    df_conc['Volume'] = df_conc['Adjusted concentration'].rdiv(m).replace([float('inf'), float('-inf')], 0).fillna(0).clip(lower=0).round(2)
    
    # 调整表格顺序
    output_frame = df_conc[['Plasmid', 'Qbit', 'Adjusted concentration', 'Volume']]

    return output_frame


def calculate_and_export_conc(plate_path: str, asc_paths: dict, c:float, b:float, a:float, scale:float, m:float):
    wb = PlateWorkbook()
    wb.read_from_excel(plate_path)
    df_conc_all = pd.DataFrame()
    for plate_name in wb.plates.keys():
        plate = wb.plates[plate_name]
        eli_reads = read_asc_column(asc_paths[plate_name])
        df_conc = calculate_plasmid_conc(plate, eli_reads, c, b, a, scale, m)
        df_conc_all = pd.concat([df_conc_all, df_conc], ignore_index=True)
    output_path = os.path.join(os.path.dirname(plate_path), f'conc.xlsx')
    df_conc_all.to_excel(output_path, index=False, header=True)
    return


def get_user_inputs():

    config_path = "config/std_curve_defaults.ini"
    # 1. 先加载历史默认值
    defaults = load_defaults(config_path)

    # 回传结果
    result = {}

    def choose_file(var):
        path = filedialog.askopenfilename()
        if path:
            var.set(path)

    def on_ok():
        # 检查路径
        plate_path = plate_var.get().strip()
        if not plate_path:
            messagebox.showerror("错误", "请先选择ELI plate布局文件")
            return
        
        # 读sheet名
        try:
            xl = pd.ExcelFile(plate_path)
            sheets = xl.sheet_names
        except Exception as e:
            messagebox.showerror("错误", f"无法读取plate xlsx：{e}")
            return
        
         # 依次为每个sheet选择asc
        asc_paths = {}
        for sheet in sheets:
            msg = f"请选择与sheet “{sheet}” 对应的吸光度.asc文件"
            # messagebox.showinfo("请选择", msg)
            path = filedialog.askopenfilename(title=msg, filetypes=[("ASC files", "*.asc"), ("All files", "*.*")])
            if not path:
                messagebox.showerror("错误", f"未选择{sheet}的asc文件")
                return
            asc_paths[sheet] = path
        
        # 检查数字
        floats = []
        for entry, var in zip(num_entries, num_vars):
            value = var.get().strip()
            try:
                num = float(value)
                floats.append(num)
            except Exception:
                messagebox.showerror("错误", f"请输入有效数字：{entry['label_text']}")
                return
            
        # 保存新默认值
        save_defaults(*floats, config_path=config_path)

        # 返回数据
        nonlocal result
        result = {
            "plate_path": plate_path,
            "asc_paths": asc_paths,
            "a": floats[0],
            "b": floats[1],
            "c": floats[2],
            "scale": floats[3],
            "m": floats[4],
            "parent": root,
        }
        # root.destroy()
        root.withdraw()
        root.quit()
    
    def on_cancel():
        root.destroy()
        return

    root = tk.Toplevel()
    root.title("输入参数")
    root.resizable(False, False)

    # 设置为顶层窗口并获得焦点
    root.transient(root.master)
    root.grab_set()

    frm = tk.Frame(root)
    frm.pack(padx=16, pady=16)

    # 1. plate布局文件选择
    plate_var = tk.StringVar()
    row = tk.Frame(frm)
    row.pack(fill='x', pady=3)
    tk.Label(row, text="ELI plate布局xlsx", width=15, anchor='e').pack(side='left')
    entry = tk.Entry(row, textvariable=plate_var, width=40)
    entry.pack(side='left', padx=5)
    tk.Button(row, text="选择", command=lambda: choose_file(plate_var)).pack(side='left')

    # 说明
    tk.Label(frm, text="标准曲线计算公式：浓度=标曲系数 * (读数 - 标曲偏置) / 标曲分母 / 缩放因子",
             fg="blue", anchor='w').pack(fill='x', pady=(16,3))

    # 数值输入
    num_labels = [
        ("标曲系数", defaults['a']),
        ("标曲分母", defaults['b']),
        ("标曲偏置", defaults['c']),
        ("缩放因子", defaults['scale']),
        ("转染量", defaults['m'])
    ]
    num_vars = [tk.StringVar(value=str(val)) for label, val in num_labels]
    num_entries = []
    for i, (label, val) in enumerate(num_labels):
        row = tk.Frame(frm)
        row.pack(fill='x', pady=2)
        lbl = tk.Label(row, text=label, width=13, anchor='e')
        lbl.pack(side='left')
        entry = tk.Entry(row, textvariable=num_vars[i], width=15, justify='right')
        entry.icursor('end')
        entry.pack(side='left')
        entry.label_text = label
        num_entries.append(entry)
        # 只允许数字和小数点
        def only_float_input(text):
            if text == "":
                return True
            try:
                float(text)
                return True
            except:
                return False
        entry.config(validate="key",
                     validatecommand=(root.register(only_float_input), "%P"))

    # 按钮
    btns = tk.Frame(frm)
    btns.pack(pady=(16,0))
    tk.Button(btns, text="确定", command=on_ok, width=12).pack(side='left', padx=8)
    tk.Button(btns, text="取消", command=on_cancel, width=12).pack(side='left', padx=8)

    root.mainloop()
    return result


def load_defaults(config_path: str | None = None):
    if config_path is None:
        config_path = str(find_config_path("std_curve_defaults.ini"))

    defaults = {
        'a': 5.0,
        'b': 3374.3,
        'c': 970.28,
        'scale': 0.51,
        'm': 1500.0
    }

    if os.path.exists(config_path):
        cfg = configparser.ConfigParser()
        cfg.read(config_path, encoding="utf-8")
        if 'params' in cfg:
            for key in defaults:
                try:
                    defaults[key] = float(cfg['params'].get(key, defaults[key]))
                except:
                    pass
    return defaults


def save_defaults(a, b, c, scale, m, config_path: str | None = None):
    # 若未指定路径，则写入 exe 同目录下的 config/
    if config_path is None:
        app_dir = get_app_dir()
        cfg_dir = app_dir / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        config_path = str(cfg_dir / "std_curve_defaults.ini")
    else:
        Path(os.path.dirname(config_path)).mkdir(parents=True, exist_ok=True)

    cfg = configparser.ConfigParser()
    cfg['params'] = {
        'a': str(a),
        'b': str(b),
        'c': str(c),
        'scale': str(scale),
        'm': str(m)
    }
    with open(config_path, "w", encoding="utf-8") as f:
        cfg.write(f)

def main():
    # a, b, c, scale, m = 5.0, 3374.3, 970.28, 0.51, 1500.0

    inputs = get_user_inputs()


    plate_path = inputs['plate_path']
    asc_paths = inputs['asc_paths']

    a, b, c, scale, m = inputs['a'], inputs['b'], inputs['c'], inputs['scale'], inputs['m']
    parent = inputs['parent']

    calculate_and_export_conc(plate_path=plate_path, asc_paths=asc_paths, c=c, b=b, a=a, scale=scale, m=m)


    # 构建弹窗统计信息
    result_msg = (
        f"处理完成！\n\n"
        f"质粒浓度计算结果: conc.xlsx \n"
    )

    messagebox.showinfo("完成", result_msg, parent=parent)

    parent.destroy()

    return

if __name__ == "__main__":
    main()
    