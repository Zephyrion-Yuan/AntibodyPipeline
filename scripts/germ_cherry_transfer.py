from core.struc_plates_96 import PlateWorkbook

import pandas as pd
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import os
from collections import defaultdict
from pathlib import Path

def strip_suffix(text):
    # 去除文本结尾的“-数字”
    return re.sub(r'-\d+$', '', str(text))


def natural_sort_key(s):
    # 用于字母数字混合排序
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s)) if text]

# 3. 定义复合排序函数
def custom_sort_key(ab):
    """复合排序：H优先于L，然后自然排序"""
    ab_str = str(ab)
    # 主要排序：H结尾在前，L结尾在后，其他在最后
    primary = 0 if ab_str.endswith('H') else 1 if ab_str.endswith('L') else 2
    # 次要排序：应用自然排序
    secondary = natural_sort_key(ab_str)
    return (primary, secondary)

def choose_file(title, filetypes):
    path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    return path

# 重链数量为H，轻链数量为L，如果H % 96 + L % 96 > 96，则分开，否则不分开。不分开的方式为：重链先填充混合板，轻链再填充混合板，同时，混合板中的重链和轻链都是升序排序后最后一部分的样本编号。
def assign_plate_positions(processed_ab):
    n = len(processed_ab)
    h_count = 0
    for v in processed_ab:
        if v.endswith('H'):
            h_count += 1
        else:
            break
    l_count = n - h_count

    # 确保目标板最多只有一个重链或一个轻链
    if h_count > 96 or l_count > 96:
        messagebox.showerror("错误", "目标板无法容纳，请减少样本量")
        raise ValueError("样本量过多")

    # 分板/混板规则
    if h_count % 96 + l_count % 96 > 96:
        dest_positions = []
        dest_plate = []
        for i in range(n):
            if i < h_count:
                h_pos_idx = i % 96 + 1
                dest_positions.append(h_pos_idx)
                h_plate_idx = i // 96 + 1
                dest_plate.append(f'cherry-H')
            else:
                cnt = i - h_count
                l_pos_idx = cnt % 96 + 1
                dest_positions.append(l_pos_idx)
                l_plate_idx = cnt // 96 + 1
                dest_plate.append(f'cherry-L')
        return dest_positions, dest_plate
    else:
        dest_positions = []
        dest_plate = []
        mix_plate_idx = h_count // 96 + 1
        mix_plate_h_cnt = h_count % 96
        l_mix_start = h_count + (l_count // 96) * 96
        for i in range(h_count):
            h_pos_idx = i % 96 + 1
            dest_positions.append(h_pos_idx)
            h_plate_idx = i // 96 + 1
            dest_plate.append(f'cherry-H')
        for i in range(h_count, l_mix_start):
            cnt = i - h_count
            l_pos_idx = cnt % 96 + 1
            dest_positions.append(l_pos_idx)
            l_plate_idx = cnt // 96 + 1
            dest_plate.append(f'cherry-L')
        for i in range(l_mix_start, n):
            l_pos_idx = i - l_mix_start + mix_plate_h_cnt + 1
            dest_positions.append(l_pos_idx)
            dest_plate.append(f'cherry-H')
        return dest_positions, dest_plate

def select_multiple_xlsx():
    paths = []
    while True:
        files = filedialog.askopenfilenames(
            title="选择含多个plate的xlsx，点击取消终止选择",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if not files:
            break   # 用户点取消 → 结束多目录选择
        paths.extend(files)

        # 询问是否继续选择其它目录
        if not messagebox.askyesno("继续？", "是否继续选择其他目录的xlsx文件？"):
            break
    return list(dict.fromkeys(paths))  # 去重并保持顺序

def select_multiple_txt():
    paths = []
    while True:
        files = filedialog.askopenfilenames(
            title="选择包含样本名的txt，点击取消终止选择",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not files:
            break   # 用户点取消 → 结束多目录选择
        paths.extend(files)

        # 询问是否继续选择其它目录
        if not messagebox.askyesno("继续？", "是否继续选择其他目录的txt文件？"):
            break
    return list(dict.fromkeys(paths))  # 去重并保持顺序

def parse_plate_idx(name):
    # 移除前缀 plate / Plate / PLATE
    name = re.sub(r'^plate[_\s-]*', '', name, flags=re.IGNORECASE).strip()

    # 再抓取纯数字
    m = re.search(r'\d+', name)
    if m:
        return int(m.group())

    raise ValueError(f"无法从 plate 名提取数字：{name}")


# 通用处理方案：适应不同数据类型
# 使用函数
# df_matched = filter_source_label(df_matched)
def filter_source_label(df):
    """
    过滤Source_label列的空值或无效值，适应不同数据类型
    """
    if "Source_label" not in df.columns:
        return df
    
    col = df["Source_label"]
    
    # 根据数据类型采取不同的过滤策略
    if col.dtype == 'object' or col.dtype == 'string':
        # 字符串类型：去除空格并过滤空值
        mask = col.fillna("").astype(str).str.strip() != ""
    elif col.dtype.kind in 'iufc':  # 整数/浮点数类型
        # 数值类型：过滤掉0或负数
        mask = col != 0
    else:
        # 其他类型：只要不是空值即可
        mask = col.notna()
    
    return df[mask]

def main():
    # 1. 选择多个 plate xlsx 和一个 txt
    root = tk.Toplevel()
    root.withdraw()
    # 允许多选 xlsx
    xlsx_paths = select_multiple_xlsx()
    txt_paths = select_multiple_txt()

    # txt_path = filedialog.askopenfilename(
    #     title="选择txt表",
    #     filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    # )

    # 注意：askopenfilenames 返回的是一个元组，没有选择时是空元组 ()
    if not xlsx_paths or not txt_paths:
        messagebox.showerror("错误", "必须至少选择一个xlsx文件和一个txt文件。")
        return

    directory = os.path.dirname(txt_paths[0])

    # 2. 读取多个 plates workbook
    workbooks = []
    new_idx = {}
    acc_idx = 0
    xlsx_wb_dict = {}
    for xlsx_path in xlsx_paths:
        wb = PlateWorkbook()
        wb.read_from_excel(xlsx_path)
        workbooks.append(wb)
        xlsx_wb_dict[wb] = xlsx_path
        new_idx[wb] = acc_idx
        acc_idx += wb.plates_num

    # 3. 读取txt
    # df_txt = pd.read_csv(txt_path, sep="\t", engine='python', header=None)

    # # 如果没有表头或只有一列
    # if df_txt.shape[1] == 1:
    #     df_txt.columns = ['Plasmid']

    # 3. 初始化一个空列表来存储每个txt的DataFrame
    df_list = []

    # 循环读取每个txt文件
    for txt_path in txt_paths:
        # 读取单个txt文件
        df_temp = pd.read_csv(txt_path, sep="\t", engine='python', header=None)
        
        # 如果没有表头或只有一列，设置列名
        if df_temp.shape[1] == 1:
            df_temp.columns = ['Plasmid']
        
        # 将当前文件的DataFrame添加到列表中
        df_list.append(df_temp)

    # 合并所有DataFrame
    df_txt = pd.concat(df_list, ignore_index=True)

    # 可选：去重（如果需要）
    df_txt = df_txt.drop_duplicates()

    # 4. 排序
    df_txt = df_txt.sort_values(
        by="Plasmid",
        key=lambda x: x.map(natural_sort_key)
    ).reset_index(drop=True)

    # 5. 初始化匹配信息（可选：如果需要记录每个plate的匹配）
    #    用 (workbook_index, plate_name) 作为键，避免不同xlsx里plate名字重复
    plas_matched = {}
    for wb in workbooks:
        plas_matched[wb] = {plate_name: set() for plate_name in wb.plates}

    output_rows = []
    found_sample = set()

    # 6. 匹配plate文本，生成标记信息
    for ab in df_txt["Plasmid"]:
        ab_norm = str(ab).strip().lower()
        found = False
        sample_name = strip_suffix(ab)

        # 遍历每一个 workbook
        for wb_idx, wb in enumerate(workbooks):
            # 遍历该 workbook 中的每一个 plate
            for plate_name, plate in wb.plates.items():
                try:
                    plate_idx = parse_plate_idx(plate_name)
                except:
                    plate_idx = 0  # 或抛错误，看你需求

                # plate_idx = re.sub(r'^plate', '', plate_name, flags=re.IGNORECASE).lstrip()
                positions = plate.get_number_by_value(ab_norm)

                if positions:
                    found = True
                    if sample_name not in found_sample:
                        found_sample.add(sample_name)

                        for pos in positions:
                            plas_matched[wb][plate_name].add(pos)

                            # 如果你想在输出中区分来自哪个xlsx，
                            # 可以在Source_label里加上文件名信息：
                            src_file = f"{plate_idx}-{os.path.basename(os.path.dirname(xlsx_paths[wb_idx]))}-{os.path.basename(xlsx_paths[wb_idx])}"
                            # src_label = plate_idx
                            src_label = new_idx[wb] + plate_idx

                            output_rows.append({
                                "Plasmid": ab,
                                "Source_file": src_file,
                                "Source_label": src_label,
                                "Source_position": pos,
                            })
                            break
                    # 找到一次就不再在其它plate重复写行
                    break
            if found:
                break

        if not found:
            # 没有匹配到，也要输出一行（Source为空）
            output_rows.append({
                "Plasmid": ab,
                "Source_file": "",
                "Source_label": "",
                "Source_position": "",
            })

    
    # 构建新的DataFrame
    df_matched = pd.DataFrame(output_rows)

    # 6. 处理Plasmid（去尾部“-数字”），不去重
    processed_ab = [strip_suffix(ab) for ab in df_matched["Plasmid"]]
    df_matched["Plasmid"] = processed_ab

    # 2. 过滤空标签行
    df_matched = df_matched.dropna(subset=["Source_label"])
    # df_matched = df_matched[df_matched["Source_label"].str.strip() != ""]
    # df_matched = df_matched[df_matched["Source_label"] >= 0]
    df_matched = filter_source_label(df_matched)


    # 4. 应用复合排序
    df_matched = df_matched.sort_values(by="Plasmid", key=lambda x: x.map(custom_sort_key))
    
    # 7. 生成Destination_position
    try:
        dest_positions, dest_plate = assign_plate_positions(df_matched["Plasmid"])
        df_matched["Destination_position"] = dest_positions
        df_matched["Destination"] = dest_plate
    except Exception as e:
        messagebox.showerror("错误", str(e))
        return

    # 9. Volume全填500
    df_matched["Volume"] = 500

    # 10. 整理输出列名并输出Excel
    output_cols = ["Source_label", "Source_position", "Destination_position", "Destination", "Volume", "Source_file", "Plasmid"]
    output_name = f"check.xlsx"
    sorted_output_name = f"worklist.xlsx"  # 排序后的文件名
    plate_output_name = f"plates.xlsx"

    out_df = df_matched.copy()
    out_df = out_df[output_cols]
    out_df.to_excel(os.path.join(directory, output_name), index=False)


    # 按 Destination_列分组并转换为字典
    grouped_data = defaultdict(list)
    for ab, dest in zip(out_df["Plasmid"], out_df["Destination"]):
        grouped_data[dest].append(ab)

    pb = PlateWorkbook()
    # 为每个 Destination_创建单独的工作表
    for dest, ab_list in grouped_data.items():
        pb.add_plate_from_list(ab_list, plate_name=dest)
    pb.write_to_excel(os.path.join(directory, plate_output_name))

    
    # 升序排序
    out_df.sort_values(by=["Destination", "Destination_position", "Source_label", "Source_position"], ascending=[True, True, True, True]).to_excel(os.path.join(directory, sorted_output_name), index=False)

    # 11. 高亮标记
    
    for wb in workbooks:
        xlsx_path = xlsx_wb_dict[wb]
        wb.highlight_and_save(xlsx_path, plas_matched[wb])
    
    result_msg = (
        f"处理完成！\n\n"
        f"转板worlists: worklist.xlsx \n"
        f"转板后布局表: check.xlsx \n"
    )

    messagebox.showinfo("完成", result_msg, parent=root)
    root.destroy
    return

if __name__ == "__main__":
    main()
