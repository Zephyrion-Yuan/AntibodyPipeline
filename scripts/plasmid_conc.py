from core.struc_plates_96 import PlateWorkbook, PlateSheet
from core.read_config_path import get_app_dir, get_meipass_dir, find_config_path

import pandas as pd
import re
from core.ui_inputs import UIContext
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
        raise ValueError("b和scale不能为0")
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
    ui = UIContext.from_env()
    defaults = load_defaults()

    plate_path = ui.require_input("plate_file")
    asc_files = ui.list_inputs("asc_files")

    xl = pd.ExcelFile(plate_path)
    sheets = xl.sheet_names
    if asc_files and len(asc_files) != len(sheets):
        raise ValueError("asc文件数量需与plate的sheet数量一致")

    asc_paths = {}
    for idx, sheet in enumerate(sheets):
        if asc_files:
            asc_paths[sheet] = asc_files[idx]
        else:
            raise ValueError(f"未提供{sheet}的asc文件")

    a = float(ui.optional_param("a", defaults["a"]))
    b = float(ui.optional_param("b", defaults["b"]))
    c = float(ui.optional_param("c", defaults["c"]))
    scale = float(ui.optional_param("scale", defaults["scale"]))
    m = float(ui.optional_param("m", defaults["m"]))

    save_defaults(a, b, c, scale, m)

    return {
        "plate_path": plate_path,
        "asc_paths": asc_paths,
        "a": a,
        "b": b,
        "c": c,
        "scale": scale,
        "m": m,
        "parent": None,
    }

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

    print(result_msg)

    if parent:
        parent.destroy()

    return

if __name__ == "__main__":
    main()
    
