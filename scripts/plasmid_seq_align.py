import os
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from Bio import SeqIO
import re

def read_templates():
    """使用文件选择器读取模板序列文件，支持 FASTA 或 AB1 格式"""
    file_path = filedialog.askopenfilename(
        title="选择模板序列文件（支持fasta或ab1）",
        filetypes=[("FASTA or AB1 files", "*.fasta *.fa *.txt *.ab1"), ("All files", "*.*")]
    )

    templates = {}
    if not file_path:
        print("未选择模板文件，程序中止。")
        return templates, None

    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext in [".fasta", ".fa", ".txt"]:
        fmt = "fasta"
    elif file_ext == ".ab1":
        fmt = "abi"
    else:
        print(f"不支持的模板文件类型：{file_path}")
        return {}, None

    try:
        if fmt == "abi":
            record = SeqIO.read(file_path, fmt)
            templates[record.id] = record.seq
        else:
            for record in SeqIO.parse(file_path, fmt):
                templates[record.id] = record.seq
    except Exception as e:
        print(f"读取模板失败：{e}")
        return {}, None
    
    # 返回templates和file_path的目录
    temp_dir = os.path.dirname(file_path)

    return templates, temp_dir

def read_sequence_files():
    """通过目录选择器读取序列文件夹，自动读取 ab1 和 fasta 文件"""
    data_dir = filedialog.askdirectory(title="选择包含待比对序列的目录")
    if not data_dir:
        print("未选择目录，程序中止。")
        return {}, None

    sequences = {}
    for file_name in os.listdir(data_dir):
        file_path = os.path.join(data_dir, file_name)
        file_ext = os.path.splitext(file_name)[1].lower()
        if not os.path.isfile(file_path):
            continue
        try:
            if file_ext == ".ab1":
                record = SeqIO.read(file_path, "abi")
                sequences[record.id] = record.seq
            elif file_ext in [".fasta", ".fa", ".seq"]:
                # record = next(SeqIO.parse(file_path, "fasta"))  # 仅取第一条
                # sequences[record.id] = record.seq
                for record in SeqIO.parse(file_path, "fasta"):
                    sequences[record.id] = record.seq
        except Exception as e:
            print(f"跳过 {file_name}，读取失败：{e}")

    return sequences, data_dir

# def analyze_samples(input_file, output_file):
#     # 存储每个样本组及其包含的编号
#     sample_groups = {}

#     # 获取输入文件的目录
#     input_dir = os.path.dirname(input_file)
#     # 构建输出文件的完整路径（与输入文件同目录）
#     output_file = os.path.join(input_dir, output_file)
    
    
#     # 读取输入文件
#     with open(input_file, 'r', encoding='utf-8') as f:
#         for line in f:
#             line = line.strip()
#             if not line:
#                 continue
            
#             # # 分割样本名，获取基础部分和编号
#             base_name = line.split('-')[0]

#             # 最后的编号（转换为整数）
#             try:
#                 number = line.split('-')[-1].split('_')[0]
#             except ValueError:
#                 continue  # 跳过编号不是数字的行
            
#             # 将编号添加到对应的样本组
#             if base_name not in sample_groups:
#                 sample_groups[base_name] = set()
#             sample_groups[base_name].add(int(number))
    
#     # 找出包含1-5所有编号的样本组
#     complete_groups = []
#     required_numbers = {1, 2, 3, 4, 5}
#     for base_name, numbers in sample_groups.items():
#         if required_numbers.issubset(numbers):
#             complete_groups.append(base_name)
    
#     # 输出结果到文件
#     with open(output_file, 'w', encoding='utf-8') as f:
#         for group in complete_groups:
#             f.write(f"{group}\n")


def find_and_report_matches(sequences, templates, output_dir, position_threshold=50000, parent=None):
    """查找模板与序列匹配并输出到输入文件夹路径（带去重写入）"""
    output_query_file = os.path.join(output_dir, "matched_output_for_query.txt")
    info_file = os.path.join(output_dir, "match_info.txt")
    mismatch_file = os.path.join(output_dir, "mismatch_info.csv")
    no_match_file = os.path.join(output_dir, "output_no_matches.txt")
    no_match_all_file = os.path.join(output_dir, "output_no_matches_all.txt")

    if not sequences:
        messagebox.showerror("错误", "输入序列为空，未进行比对。", parent=parent)
        return
    if not templates:
        messagebox.showerror("错误", "模板序列为空，未进行比对。", parent=parent)
        return
    
    # 记录所有子样本（按父样本分组）
    all_samples = {}

    # 记录正确匹配的子样本（按父样本分组）
    correct_samples = {}

    # 用来收集去重后的输出内容
    info_lines = set()
    mismatch_lines = set()
    no_match_lines = set()
    matched_query_lines = set()

    total_matches = 0
    total_mismatches = 0
    files_with_no_match = 0

    try:
        for seq_file, seq in sequences.items():
            # 统一处理文件名
            processed_seq_file = re.sub(r'-CMV.*$', '', seq_file)
            processed_seq_file = (
                processed_seq_file
                .replace("-", "_")
                .replace("_H_", "_H-")
                .replace("_L_", "_L-")
            )

            base_name = processed_seq_file.split('-')[0]
            all_samples.setdefault(base_name, set()).add(processed_seq_file)
            
            seq_upper = str(seq).upper()
            found = False

            for template_id, template_seq in templates.items():
                template_upper = str(template_seq).upper()
                template_id_in_file = template_id.lower() in seq_file.lower()
                start_index = seq_upper.find(template_upper)

                if start_index != -1:
                    end_index = start_index + len(template_upper)
                    # 位置符合
                    if 0 <= start_index < position_threshold:
                        found = True

                        if template_id_in_file:
                            # 正常匹配
                            matched_query_lines.add(f"{processed_seq_file}\n")
                            correct_samples.setdefault(base_name, set()).add(processed_seq_file)
                            info_lines.add(f"{template_id} found in {seq_file} at positions {start_index} to {end_index}\n")
                            total_matches += 1
                        else:
                            # 序列匹配到了，但名字不一致
                            # mismatch_lines.add(
                            #     "Warning: Sequence match found for {} in {} at positions {} to {}, "
                            #     "but name does not match.\n".format(
                            #         template_id, seq_file, start_index, end_index
                            #     )
                            # )
                            seq_name = processed_seq_file = re.sub(r'-CMV.*$', '', seq_file)
                            mismatch_lines.add(
                                "{},{},{},{},name does not match,\n".format(
                                    template_id, seq_name, start_index, end_index
                                )
                            )
                            total_mismatches += 1

            if not found:
                files_with_no_match += 1
                processed_seq_file = re.sub(r'-CMV.*$', '', seq_file)
                processed_seq_file = (
                    processed_seq_file
                    .replace("-", "_")
                    .replace("_H_", "_H-")
                    .replace("_L_", "_L-")
                )
                no_match_lines.add(f"{processed_seq_file}\n")

        # 统一写入文件（已经去重）
        with open(info_file, "w") as f:
            for line in sorted(info_lines):
                f.write(line)

        with open(mismatch_file, "w") as f:
            f.write("False_template,Seq_name,Aligned_start,Aligned_end,Warning,\n")
            for line in sorted(mismatch_lines):
                f.write(line)

        with open(no_match_file, "w") as f:
            for line in sorted(no_match_lines):
                f.write(line)

        with open(output_query_file, "w") as f:
            for line in sorted(matched_query_lines):
                f.write(line)
        

        zero_correct_samples = []

        for base_name, subs in all_samples.items():
            correct = correct_samples.get(base_name, set())
            if len(correct) == 0:
                zero_correct_samples.append(base_name)
        
        with open(no_match_all_file, "w", encoding="utf-8") as f:
            for name in sorted(zero_correct_samples):
                f.write(f"{name}\n")


        # # 写完之后再判断有没有“未匹配”的文件，如果有再分析
        # if os.path.exists(no_match_file) and os.path.getsize(no_match_file) > 0:
        #     # 调用分析函数，输入为 output_no_matches.txt，输出为 output_no_matches_all.txt
        #     analyze_samples(input_file=no_match_file, output_file=no_match_all_file)
        # else:
        #     print("未找到有效匹配的序列文件，跳过样本组分析。")

    except Exception as e:
        messagebox.showerror("写入错误", f"❌ 文件写入过程中发生错误：\n{e}", parent=parent)


    
    # 构建弹窗统计信息
    result_msg = (
        f"比对完成！\n\n"
        f"正确匹配（匹配成功且命名一致）：{total_matches}\n"
        f"匹配成功但名称不一致：{total_mismatches}\n"
        f"未匹配到任何模板：{files_with_no_match} 个文件\n\n"
        # f"输出文件路径：\n"
        # f"- 完全匹配序列：{os.path.basename(output_file)}\n"
        # f"- 完全匹配序列规范名：{os.path.basename(output_query_file)}\n"
        # f"- 匹配详细信息：{os.path.basename(info_file)}\n"
        # f"- 名称不一致序列：{os.path.basename(mismatch_file)}\n"
        # f"- 未匹配序列：{os.path.basename(no_match_file)}"
    )

    messagebox.showinfo("比对结果", result_msg)

    return

def main():
    root = tk.Toplevel()
    root.withdraw()  # 隐藏主窗口

    templates, temp_dir = read_templates()
    if not templates:
        return

    sequences, data_dir = read_sequence_files()
    if not sequences:
        return

    find_and_report_matches(sequences, templates, output_dir=temp_dir, parent=root)
    root.destroy
    return

if __name__ == "__main__":
    main()
