from core.struc_plates_96 import PlateWorkbook, PlateSheet

import pandas as pd
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import os


def natural_key(string):
    # 用tuple替代list, tuple可hash
    return tuple(int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(string)))

def merge_h_l_output(plates_path, conc_path, pair_path):
    # 新建目标DataFrame
    columns = [
        "H_plasmid", "H_source_label", "H_source_position", "H_volume",
        "L_plasmid", "L_source_label", "L_source_position", "L_volume",
        "Destination_label", "Destination_position", "Antibody_name",
    ]

    merged_records = []
    wb = PlateWorkbook()
    wb.read_from_excel(plates_path)

    # f_conc = pd.read_excel(conc_path)

    # 读取所有sheet，返回一个字典，key是sheet名，value是对应的DataFrame
    all_sheets = pd.read_excel(conc_path, sheet_name=None)

    # 由于每个sheet的header一样，直接合并所有DataFrame
    f_conc = pd.concat(all_sheets.values(), ignore_index=True)

    f_pair = pd.read_excel(pair_path)

    count = 1

    for _, pair_row in f_pair.iterrows():
        h_plas = pair_row['chain_H']
        l_plas = pair_row['chain_L']
        ab_name = pair_row['antibody']

        h_conc_row = f_conc.query(f'Plasmid == "{h_plas}"')
        if h_conc_row.empty:
            continue
        # 液体量大于40的取40
        # h_vol = float(h_conc_row['Volume'].iloc[0])
        h_vol = min(40.0, float(h_conc_row['Volume'].iloc[0]))

        l_conc_row = f_conc.query(f'Plasmid == "{l_plas}"')
        if l_conc_row.empty:
            continue
        # 液体量大于40的取40
        # l_vol = float(l_conc_row['Volume'].iloc[0])
        l_vol = min(40.0, float(l_conc_row['Volume'].iloc[0]))
        
        h_found = False
        for h_plate_name, h_plate in wb.plates.items():
            h_positions = h_plate.get_number_by_value(h_plas.lower())
            for h_pos in h_positions:
                if not h_plate.is_accessible(h_pos, h_vol):
                    continue
                if h_vol == 0:
                    continue
                # L查找
                for l_plate_name, l_plate in wb.plates.items():
                    l_positions = l_plate.get_number_by_value(l_plas.lower())
                    for l_pos in l_positions:
                        if not l_plate.is_accessible(l_pos, l_vol):
                            continue
                        if l_vol == 0:
                            continue
                        # 找到配对，记录
                        merged_records.append({
                            "H_plasmid": h_plas,
                            "H_source_label": h_plate_name,
                            "H_source_position": h_pos,
                            "H_volume": h_vol,
                            "L_plasmid": l_plas,
                            "L_source_label": l_plate_name,
                            "L_source_position": l_pos,
                            "L_volume": l_vol,
                            "Destination_label": (count - 1) // 96 + 1,
                            "Destination_position": (count - 1) % 96 + 1,
                            "Antibody_name": ab_name,
                        })
                        # 体积扣除
                        h_plate.take_volume(h_pos, h_vol)
                        l_plate.take_volume(l_pos, l_vol)
                        count += 1
                        h_found = True
                        break
                    if h_found:
                        break
                if h_found:
                    break
            if h_found:
                break
    
    if len(merged_records) == 0:
        messagebox.showinfo("提示", "没有找到配对！")
        return


    merged_df = pd.DataFrame(merged_records, columns=columns)

    # 高亮
    highlight_dict = {}
    for plate_name in wb.plates.keys():
        highlight_dict[plate_name] = set()
    for row in merged_records:
        highlight_dict[row["H_source_label"]].add(row["H_source_position"])
        highlight_dict[row["L_source_label"]].add(row["L_source_position"])

    wb.highlight_and_save(plates_path, highlight_dict)

    # 按照重命名后样本名调整顺序
    dest_label_raw = merged_df["Destination_label"].copy().reset_index(drop=True)
    dest_pos_raw = merged_df["Destination_position"].copy().reset_index(drop=True)


    # # 生成辅助排序列
    # merged_df['H_plasmid modified key'] = merged_df['H_plasmid'].map(natural_key)

    # 排序
    merged_df = merged_df.sort_values(
        by=[
            'Antibody_name',
            'H_source_label',
            'L_source_label',
            'H_source_position',
            'L_source_position'
        ],
        ascending=[True, True, True, True, True]
    ).reset_index(drop=True)

    # # 删掉辅助列
    # merged_df = merged_df.drop(columns=['H_plasmid modified key'])

    merged_df["Destination_label"] = dest_label_raw
    merged_df["Destination_position"] = dest_pos_raw    

    return merged_df


def export_merged_df(merged_df, output_path, filename):
    """
    将merged_df按需求分别输出到Excel三个sheet中。
    - sheet3: check_output，全部内容
    - sheet1: H_worklist，仅H相关字段
    - sheet2: Lworklist，仅L相关字段
    """

    # 替换"Destination_label"列中的指定值
    # 选中需要替换的两列，用一个字典批量替换
    merged_df[["H_source_label", "L_source_label"]] = merged_df[["H_source_label", "L_source_label"]].replace(
        {"cherry-H": "plasmid-H", "cherry-L": "plasmid-L"}
    )

    # 准备每个子表
    h_columns = [
        "H_source_label", "H_source_position", 
        "Destination_position", "Destination_label", "H_volume", "H_plasmid"
    ]
    l_columns = [
        "L_source_label", "L_source_position", 
        "Destination_position", "Destination_label", "L_volume", "L_plasmid"
    ]
    h_worklist = merged_df[h_columns].copy()
    l_worklist = merged_df[l_columns].copy()

    file_full_path = os.path.join(output_path, filename)

    # 写入Excel三个sheet
    with pd.ExcelWriter(file_full_path, engine='openpyxl') as writer:
        # sheet3: 全部内容
        merged_df.to_excel(writer, sheet_name='check_output', index=False)
        # sheet1: H_worklist
        h_worklist.to_excel(writer, sheet_name='H_worklist', index=False)
        # sheet2: Lworklist
        l_worklist.to_excel(writer, sheet_name='L_worklist', index=False)
    
    out_plates = {}
    # 按Destination_label分组
    for label, group in merged_df.groupby('Destination_label'):
        # 按Destination_position排序（确保板内顺序一致）
        group_sorted = group.sort_values('Destination_position')
        antibodies = group_sorted['Antibody_name'].tolist()
        # 拆分为多个长度<=96的list
        split_lists = [antibodies[i:i+96] for i in range(0, len(antibodies), 96)]
        out_plates[label] = split_lists if len(split_lists) > 1 else split_lists[0]
    
    pw = PlateWorkbook()
    for label, plate_data in out_plates.items():
        plate_name = f"h_l_plate{label}"
        pw.add_plate_from_list(plate_data, plate_name=plate_name)
    pw.write_to_excel(os.path.join(output_path, f"plasmids_h_l_plate.xlsx"))

    save_quarter_sheets_to_excel(out_plates, os.path.join(output_path, f"cell_plates.xlsx"))

    # 使用示例
    # export_merged_df(merged_df, "output.xlsx")
    return


def split_plate_to_quarters(plate_data, sheet_name):
    """
    plate_data: 长度96的list，列优先填充（8行12列）
    返回: dict {f"{sheet_name}_{num}": 4x6子板list, ...}
    """
    # 转为8x12的二维数组，列优先
    arr = [["" for _ in range(12)] for _ in range(8)]
    idx = 0
    for col in range(12):
        for row in range(8):
            arr[row][col] = plate_data[idx] if idx < len(plate_data) else ""
            idx += 1

    # 按4x6切成4块，编号从左上顺时针或从左到右、上到下都可以，这里默认左上-右上-左下-右下
    blocks = {}
    coords = [
        (0, 0),   # 左上起点
        (4, 0),   # 左下起点
        (0, 6),   # 右上起点
        (4, 6),   # 右下起点
    ]
    for num, (r0, c0) in enumerate(coords, 1):
        block = []
        for col in range(c0, c0 + 6):
            for row in range(r0, r0 + 4):
                block.append(arr[row][col])
        blocks[f"{sheet_name}_{num}"] = block
    
    return blocks


def save_quarter_sheets_to_excel(out_plates, output_path):
    all_blocks = {}

    for label, plates in out_plates.items():
        # 多板/单板兼容
        plates_list = plates if isinstance(plates[0], list) else [plates]
        for idx, plate_data in enumerate(plates_list, 1):
            base_name = f"{label}_{idx}" if len(plates_list) > 1 else f"{label}"
            sub_blocks = split_plate_to_quarters(plate_data, base_name)
            all_blocks.update(sub_blocks)

    # 写入Excel，每个子板一个sheet（4x6表格，列优先）
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for block_name, block_data in all_blocks.items():
            # 转为4x6的二维表，列优先
            arr = [[ "" for _ in range(6)] for _ in range(4)]
            idx = 0
            for col in range(6):
                for row in range(4):
                    arr[row][col] = block_data[idx] if idx < len(block_data) else ""
                    idx += 1
            df = pd.DataFrame(arr, index=['A', 'B', 'C', 'D'], columns=[f'{j+1}' for j in range(6)])
            df.to_excel(writer, sheet_name=block_name, index=True)


def get_user_inputs():

    # 回传结果
    result = {}

    def choose_file(var):
        path = filedialog.askopenfilename()
        if path:
            var.set(path)

    def on_ok():
        # 检查路径
        paths = []
        for var in path_vars:
            value = var.get().strip()
            if not value:
                messagebox.showerror("错误", "所有路径不能为空")
                return
            paths.append(value)

        # 返回数据
        nonlocal result
        result = {
            "plates_path": paths[0],
            "conc_path": paths[1],
            "pair_path": paths[2],
            "parent": root,
        }
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

    # 路径输入
    path_labels = ["布局表", "浓度表", "配对表"]
    path_vars = [tk.StringVar() for _ in range(3)]
    for i, label in enumerate(path_labels):
        row = tk.Frame(frm)
        row.pack(fill='x', pady=3)
        tk.Label(row, text=label, width=13, anchor='e').pack(side='left')
        entry = tk.Entry(row, textvariable=path_vars[i], width=40)
        entry.pack(side='left', padx=5)
        btn = tk.Button(row, text="选择", command=lambda v=path_vars[i]: choose_file(v))
        btn.pack(side='left')

    row = tk.Frame(frm)
    row.pack(fill='x', pady=8)

    # 按钮
    btns = tk.Frame(frm)
    btns.pack(pady=(16,0))
    tk.Button(btns, text="确定", command=on_ok, width=12).pack(side='left', padx=8)
    tk.Button(btns, text="取消", command=on_cancel, width=12).pack(side='left', padx=8)

    root.mainloop()
    return result


def main():

    inputs = get_user_inputs()

    plates_path = inputs['plates_path']
    conc_path = inputs['conc_path']
    pair_path = inputs['pair_path']

    output_path = os.path.dirname(plates_path)

    h_l_output = merge_h_l_output(plates_path=plates_path, conc_path=conc_path, pair_path=pair_path)

    export_merged_df(h_l_output, output_path, "transfer_worklists_and_check.xlsx")

    # 构建弹窗统计信息
    result_msg = (
        f"处理完成！\n\n"
        f"转板worlists和check: transfer_worklists_and_check.xlsx \n"
        f"转板后布局表: plasmids_h_l_plate.xlsx \n"
        f"重链转板样本已高亮在: higlighted_plas_h_plate.xlsx \n"
        f"轻链转板样本已高亮在: higlighted_plas_l_plate.xlsx \n"
        f"转染细胞布局: cell_plates.xlsx \n"
    )

    messagebox.showinfo("完成", result_msg, parent=inputs['parent'])
    inputs['parent'].destroy()
    
    return

if __name__ == "__main__":
    main()
    