import pandas as pd
from collections import defaultdict
from dnachisel import *
# from dnachisel.builtin_specifications import load_codon_table
from core.ui_inputs import UIContext
import json
from pathlib import Path
import configparser
from Bio.Seq import Seq
import configparser, os
from core.read_config_path import get_app_dir, get_meipass_dir, find_config_path
def load_codon_table(organism='human'):
    codon_json_path = find_config_path(f'codon_{organism}.json')
    with open(codon_json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_defaults(config_path: str | None = None):
    if config_path is None:
        config_path = str(find_config_path('hr_arms.ini'))
    defaults = {
        'IgG1/4 HC-F': 'gctacaggcgtgcatagt',
        'IgG4 HC-R': 'gctagcaccaagggcccatcggtc',
        'IgG1 HC-R': 'gctagcaccaagggccctagcgtg',
        'kappa LC-F': 'gctacaggcgtgcatagt',
        'kappa LC-R': 'cgtacggtggctgcaccatctgtc',
        'lambda LC-F': 'gctacaggcgtgcatagt',
        'lambda LC-R': 'ggccagcccaaggccgcc',
    }
    if os.path.exists(config_path):
        cfg = configparser.ConfigParser()
        cfg.read(config_path, encoding="utf-8")
        if 'params' in cfg:
            for key in defaults:
                defaults[key] = str(cfg['params'].get(key, defaults[key]))
    return defaults

def save_defaults(params: dict, config_path="config/hr_arms.ini"):
    # 默认写到 exe 同目录 config/hr_arms.ini（注意：若放在受限目录，可能需要管理员权限）
    if config_path is None:
        app_dir = get_app_dir()
        cfg_dir = app_dir / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        config_path = str(cfg_dir / "hr_arms.ini")
    else:
        Path(os.path.dirname(config_path)).mkdir(parents=True, exist_ok=True)

    cfg = configparser.ConfigParser()
    cfg['params'] = params
    with open(config_path, 'w', encoding="utf-8") as f:
        cfg.write(f)

def detect_light_chain_type(light_aa: str) -> str | None:
    """根据轻链AA末尾判断是kappa还是lambda，识别不了返回None"""
    light_aa = light_aa.strip().upper()
    if light_aa.endswith(("EIK", "DIK", "PGK", "GPK", "VVK", "VVR")): 
    # if light_aa.endswith(("EIK", "DIK")):
        return "kappa"
    if light_aa.endswith(("TVL", "DRP", "IIL", "IVT", "TVT")):
        return "lambda"
    return None

# DNACHISEL密码子优化
# ------------工具函数----------
def table_to_usage_dict(codon_table):
    """
    将 {AA: {codon: freq}} 展开为 {codon: freq_norm}。
    以每个 AA 内部归一化，避免输入小数误差。
    """
    usage = {}
    for aa, d in codon_table.items():
        total = sum(d.values()) or 1.0
        for codon, f in d.items():
            usage[codon.upper()] = float(f) / total
    return usage


def aa_to_codons_from_table(codon_table):
    """从你的 JSON 表导出 AA->同义密码子列表（全大写）。"""
    aa2codons = {}
    for aa, d in codon_table.items():
        aa2codons[aa] = sorted([c.upper() for c in d.keys()])
    return aa2codons

def gc_fraction(seq):
    gc = sum(1 for b in seq if b in 'GCgc')
    return gc / len(seq) if seq else 0.0

def codon_gc_count(c):
    c = c.upper()
    return (c[0] in 'GC') + (c[1] in 'GC') + (c[2] in 'GC')

def split_codons(dna):
    return [dna[i:i+3] for i in range(0, len(dna), 3)]

def join_codons(codons):
    return ''.join(codons)

def window_gc_penalty(seq, target_min, target_max, window=None):
    """
    对每个窗口计算 GC 偏离的“超出区间”量并累加。
    - window=None 时仅计算全局一次；
    - 否则对所有窗口滑动累加（步长=1个核苷）。
    """
    if window is None or window <= 0 or window >= len(seq):
        g = gc_fraction(seq)
        if target_min <= g <= target_max:
            return 0.0
        return min(abs(g - target_min), abs(g - target_max)) if g < target_min or g > target_max else 0.0

    n = len(seq)
    if n < window:
        return window_gc_penalty(seq, target_min, target_max, window=None)

    # 预计算前缀 GC 计数，O(n)
    pref_gc = [0]*(n+1)
    for i, b in enumerate(seq, 1):
        pref_gc[i] = pref_gc[i-1] + (1 if b in 'GCgc' else 0)

    pen = 0.0
    for start in range(0, n-window+1):
        end = start + window
        gc_w = (pref_gc[end] - pref_gc[start]) / window
        if gc_w < target_min:
            pen += (target_min - gc_w)
        elif gc_w > target_max:
            pen += (gc_w - target_max)
    return pen


def check_translation(dna_seq, aa_seq):
    translated = str(Seq(dna_seq).translate(to_stop=False))
    assert translated == aa_seq, "Translation mismatch!"


def check_gc_and_report(
    dna_seq,
    gc_min=0.40,
    gc_max=0.70,
    window=None,             # 例如 90 或 120；None=只验全局
    strict=False,            # True: 不达标直接抛错；False: 返回报告
    atol=1e-6                # 浮点容忍
):
    def gc_fraction(seq):
        gc = sum(1 for b in seq if b in 'GCgc')
        return gc / len(seq) if seq else 0.0

    report = {
        "ok": True,
        "global_gc": None,
        "global_ok": None,
        "window": window,
        "window_ok": True,
        "violations": []   # 列出每个不达标窗口: {"start": i, "end": j, "gc": x, "delta": y, "type": "low/high"}
    }

    # 1) 全局 GC
    g = gc_fraction(dna_seq)
    report["global_gc"] = g
    report["global_ok"] = (gc_min - atol <= g <= gc_max + atol)
    if not report["global_ok"]:
        report["ok"] = False

    # 2) 窗口 GC（如启用）
    if window and window > 0 and window < len(dna_seq):
        n = len(dna_seq)
        # 前缀 GC 计数
        pref = [0]*(n+1)
        for i,ch in enumerate(dna_seq,1):
            pref[i] = pref[i-1] + (1 if ch in 'GCgc' else 0)
        for s in range(0, n - window + 1):
            e = s + window
            gc_w = (pref[e] - pref[s]) / window
            if gc_w < gc_min - atol:
                report["ok"] = False
                report["window_ok"] = False
                report["violations"].append({
                    "start": s, "end": e, "gc": gc_w,
                    "delta": gc_min - gc_w, "type": "low"
                })
            elif gc_w > gc_max + atol:
                report["ok"] = False
                report["window_ok"] = False
                report["violations"].append({
                    "start": s, "end": e, "gc": gc_w,
                    "delta": gc_w - gc_max, "type": "high"
                })
    else:
        report["window"] = None  # 未启用窗口检查

    if strict and not report["ok"]:
        # 抛出清晰的错误，告诉你到底哪里没过线
        msgs = [f"Global GC={g:.3f} not in [{gc_min:.2f}, {gc_max:.2f}]."] if not report["global_ok"] else []
        if report["violations"]:
            first = report["violations"][0]
            msgs.append(
                f"Window GC violated (example {first['start']}..{first['end']}): "
                f"{first['gc']:.3f} ({first['type']}, Δ={first['delta']:.3f}). "
                f"Total {len(report['violations'])} violating windows."
            )
        raise ValueError("GC acceptance failed: " + " ".join(msgs))

    return report


# ---------- 核心：仅同义替换的 GC 修复 ----------
def greedy_fix_gc_by_synonymous_subs(
    aa_seq,
    dna_seq,
    codon_usage,             # dict: codon -> freq
    aa2codons,               # dict: AA -> [codons]
    target_min=0.40,
    target_max=0.70,
    window=None,             # 例如 90 或 120；None 表示只看全局
    usage_weight=1.0,        # 对常用密码子的偏好（越大越强）
    gc_weight=4.0,           # 对 GC 目标的权重（越大越“执着”）
    rare_floor=1e-6,         # 防止 log(0) 等情况（若你改成对数评分时会用到）
    max_iters=20000
):
    """
    在保证氨基酸序列不变的前提下，通过同义替换把 GC 推回 [min, max] / 窗口 GC 也尽量合规。
    """
    codons = split_codons(dna_seq)
    assert len(codons) == len(aa_seq), "DNA 长度必须是 3 的倍数且和氨基酸序列对齐"

    def score(codons_now):
        seq = join_codons(codons_now)
        # GC 罚分：窗口化偏离累加 or 全局偏离
        gc_pen = window_gc_penalty(seq, target_min, target_max, window=window)

        # 使用频率“负惩罚”：频率越高越好
        use_pen = 0.0
        for c in codons_now:
            use_pen -= codon_usage.get(c.upper(), 0.0)

        # 总评分（越小越好）
        return gc_weight * gc_pen + usage_weight * use_pen

    current_score = score(codons)
    iters = 0

    while iters < max_iters:
        iters += 1
        best_delta = 0.0
        best_pos = None
        best_new = None

        for i, (aa, c0) in enumerate(zip(aa_seq, codons)):
            choices = aa2codons.get(aa, [c0])
            if len(choices) <= 1:
                continue
            for c1 in choices:
                if c1 == c0:
                    continue
                codons[i] = c1
                new_score = score(codons)
                delta = current_score - new_score
                if delta > best_delta:
                    best_delta = delta
                    best_pos = i
                    best_new = c1
            # 回溯
            codons[i] = c0

        if best_pos is None:
            break  # 没有任何可改进的同义替换
        codons[best_pos] = best_new
        current_score -= best_delta

        # 若全局已入区间且窗口罚分≈0，提前退出
        seq_now = join_codons(codons)
        if (target_min <= gc_fraction(seq_now) <= target_max) and (window_gc_penalty(seq_now, target_min, target_max, window) == 0.0):
            break

    return join_codons(codons)



# ---------- 和 DNACHISEL 集成 ----------
def codon_optimize_dnachisel(
    aa_seq,
    organism='human',
    gc_min=0.40,
    gc_max=0.70,
    window=100,            # 例如 90/120；None=不启用窗口
    usage_weight=1.0,
    gc_weight=4.0
):
    # 1) 反向翻译：建议用你原来的 reverse_translate 或其它可靠方法
    dna_seq = reverse_translate(aa_seq, table="Standard")

    # 2) 常规密码子优化（保翻译不变；去掉 EnforceGCContent 硬约束）
    codon_table = load_codon_table(organism=organism)        # 你的 JSON
    problem = DnaOptimizationProblem(
        sequence=dna_seq,
        constraints=[EnforceTranslation()],  # 只保翻译不变
        objectives=[CodonOptimize(codon_usage_table=codon_table, method='match_codon_usage')]
    )
    problem.optimize()
    dna_seq = str(problem.sequence)

    # 3) 二次“仅同义替换”GC 修复
    codon_usage = table_to_usage_dict(codon_table)           # {codon: freq}
    aa2codons = aa_to_codons_from_table(codon_table)         # {AA: [codons]}
    dna_seq = greedy_fix_gc_by_synonymous_subs(
        aa_seq=aa_seq,
        dna_seq=dna_seq,
        codon_usage=codon_usage,
        aa2codons=aa2codons,
        target_min=gc_min,
        target_max=gc_max,
        window=window,
        usage_weight=usage_weight,
        gc_weight=gc_weight
    )

    # 先做翻译一致性校验（绝对不改氨基酸）
    check_translation(dna_seq, aa_seq)  # 如前面给你的小函数

    # 再做 GC 验收；strict=True 时，不达标直接抛错
    gc_report = check_gc_and_report(
        dna_seq,
        gc_min=gc_min,
        gc_max=gc_max,
        window=window,
        strict=False   # 你也可以设 True
    )
    return dna_seq, gc_report


def process_excel_advanced(
    input_path,
    homology_heavy_f,
    homology_heavy_r,
    homology_light_f,
    homology_light_r,
    organism='human',
    parent=None,
    defaults: dict | None = None,   # >>> 新增一个可选defaults，这样可以传入load_defaults()的结果
):
    input_file = Path(input_path)
    file_name = input_file.stem
    out_all = input_file.with_stem(f"{file_name}_Synthesis_check")
    out_syn = input_file.with_stem(f"{file_name}_Synthesis")
    out_multi = input_file.with_stem(f"{file_name}_Multi")
    out_pair = input_file.with_stem(f"{file_name}_Pairs")
    df = pd.read_excel(input_path, header=0)
    df.columns = df.columns.str.lower()
    df = df.map(lambda x: str(x).replace('\n', '').replace('\r', '') if isinstance(x, str) else x)
    df = df.fillna('')

    heavy_name_col = 'id'
    heavy_col = 'vh'
    light_name_col = 'id'
    light_col = 'vl'

    new_rows = []
    pair_rows = []
    syn_rows_h = []
    syn_rows_l = []

    heavy_aa_cache = {}
    light_aa_cache = {}

    heavy_full_cache = {}
    light_full_cache = {}

    # 如果没传，就读一遍
    if defaults is None:
        defaults = load_defaults(None)

    total = len(df)
    prog = ProgressDialog(parent=parent, title="正在处理序列…", maximum=max(1, total))
    prog.update(0, f"共 {total} 条记录，开始处理…")

    reverse_defaults = {v: k for k, v in defaults.items()}

    # 重链类型的判断逻辑
    def detect_heavy_chain_type(heavy_f_seq, heavy_r_seq):
        """
        根据重链上下游序列判断重链类型
        """
        # 构建完整的重链序列模式进行匹配
        # heavy_f_key = reverse_defaults.get(heavy_f_seq.lower(), None)
        heavy_r_key = reverse_defaults.get(heavy_r_seq.lower(), None)
        
        if heavy_r_key and 'IgG4 HC-R' in heavy_r_key:
            return 'IgG4'
        elif heavy_r_key and 'IgG1 HC-R' in heavy_r_key:
            return 'IgG1'
        return 'Unknown'

    try:
        for idx, row in df.iterrows():
            h_basename = str(row[heavy_name_col]).strip().replace("-", "_")
            heavy_aa = str(row[heavy_col]).strip().upper()
            l_basename = str(row[light_name_col]).strip().replace("-", "_")
            light_aa = str(row[light_col]).strip().upper()

            # ====== 这里做轻链类型自动识别 ======
            light_type = detect_light_chain_type(light_aa)
            if light_type == "kappa":
                cur_homology_light_f = defaults.get('kappa LC-F', homology_light_f)
                cur_homology_light_r = defaults.get('kappa LC-R', homology_light_r)
            elif light_type == "lambda":
                cur_homology_light_f = defaults.get('lambda LC-F', homology_light_f)
                cur_homology_light_r = defaults.get('lambda LC-R', homology_light_r)
            else:
                # 识别不了就用调用时传进来的
                cur_homology_light_f = homology_light_f
                cur_homology_light_r = homology_light_r
            # ===================================

            # 重链类型自动识别
            heavy_type = detect_heavy_chain_type(homology_heavy_f, homology_heavy_r)

            # 重链缓存
            if heavy_aa not in heavy_aa_cache:
                heavy_nt, h_check = codon_optimize_dnachisel(heavy_aa, organism)
                heavy_full = homology_heavy_f.lower() + heavy_nt + homology_heavy_r.lower()
                heavy_aa_cache[heavy_aa] = (heavy_nt, heavy_full)
            else:
                heavy_nt, heavy_full = heavy_aa_cache[heavy_aa]

            # 轻链缓存要注意：同一条AA如果有不同的同源臂，就不能共用同一结果
            # 所以这里的key要把同源臂也加进去，避免混淆
            light_cache_key = (light_aa, cur_homology_light_f, cur_homology_light_r)
            if light_cache_key not in light_aa_cache:
                light_nt, l_check = codon_optimize_dnachisel(light_aa, organism)
                light_full = cur_homology_light_f.lower() + light_nt + cur_homology_light_r.lower()
                light_aa_cache[light_cache_key] = (light_nt, light_full)
            else:
                light_nt, light_full = light_aa_cache[light_cache_key]

            # 去重操作（名称复用）
            if heavy_full in heavy_full_cache:
                h_name = heavy_full_cache[heavy_full][0]
                heavy_full_cache[heavy_full][1] += 1
            else:
                h_name = f"{h_basename}_H"
                heavy_full_cache[heavy_full] = [h_name, int(1)]

            if light_full in light_full_cache:
                l_name = light_full_cache[light_full][0]
                light_full_cache[light_full][1] += 1
            else:
                l_name = f"{l_basename}_L"
                light_full_cache[light_full] = [l_name, int(1)]

            ab_name = h_basename if h_basename == l_basename else f"{h_basename}-{l_basename}"

            new_rows.append({
                "新重链名": h_name,
                "重链核酸序列": heavy_full,
                "重链AA": heavy_aa,
                "重链链型": heavy_type if heavy_type else "Unknown",
                "新轻链名": l_name,
                "轻链核酸序列": light_full,
                "轻链AA": light_aa,
                "轻链链型": light_type if light_type else "Unknown",
            })

            pair_rows.append({
                "chain_H": h_name,
                "chain_L": l_name,
                "antibody": ab_name,
            })

            syn_rows_h.append({
                "名称": h_name,
                "核苷酸序列": heavy_full,
                "氨基酸序列": heavy_aa,
                "链型": heavy_type if heavy_type else "Unknown",
            })
            syn_rows_l.append({
                "名称": l_name,
                "核苷酸序列": light_full,
                "氨基酸序列": light_aa,
                "链型": light_type if light_type else "Unknown",
            })

            prog.update(idx + 1, f"正在处理：{idx + 1}/{total}（{h_name} / {l_name}）")

        # 按照链型、新重链名排序
        new_cols_df = pd.DataFrame(new_rows).sort_values(by=['轻链链型', '新重链名'])
        new_cols_df.to_excel(out_all, index=False)

        pairs_df = pd.DataFrame(pair_rows)
        pairs_df.to_excel(out_pair, index=False)

        # 统一添加计数列 - 直接根据核苷酸序列查询缓存
        def lookup_count(nucleotide_seq):
            # 先在重链缓存中查找
            if nucleotide_seq in heavy_full_cache:
                return heavy_full_cache[nucleotide_seq][1]
            # 再在轻链缓存中查找
            elif nucleotide_seq in light_full_cache:
                return light_full_cache[nucleotide_seq][1]
            else:
                return 1  # 默认计数
        
        syn_df = pd.concat([pd.DataFrame(syn_rows_h).sort_values(by=['名称']), pd.DataFrame(syn_rows_l).sort_values(by=['链型', '名称'])])
        syn_df = syn_df.drop_duplicates(subset=['核苷酸序列', '名称'])
        syn_df['计数'] = syn_df['核苷酸序列'].apply(lookup_count)
        syn_df.to_excel(out_syn, index=False)

        # 提取计数大于1的序列
        syn_multi_df = syn_df[syn_df['计数'] > 1]
        syn_multi_df.to_excel(out_multi, index=False)

        result_msg = (
            f"处理完成！\n\n"
            f"检查表: {file_name}_Synthesis_check.xlsx \n"
            f"合成表结果: {file_name}_Synthesis.xlsx \n"
            f"匹配表: {file_name}_Pairs.xlsx \n"
            f"重复表: {file_name}_Multi.xlsx \n"
        )

        prog.close()
        print(result_msg)

    except Exception as e:
        prog.close()
        raise ValueError(f"处理过程中出现问题：\n{e}") from e


class ProgressDialog:
    """控制台进度提示。"""

    def __init__(self, parent=None, title="正在处理...", maximum=100):
        self.maximum = maximum
        self.title = title
        self.current = 0
        print(title)

    def set_max(self, maximum):
        self.maximum = maximum

    def update(self, value, message=None):
        self.current = value
        if message:
            print(message)

    def _refresh(self):
        return None

    def close(self):
        return None



def get_inputs():
    ui = UIContext.from_env()
    config_path = "config/hr_arms.ini"
    defaults = load_defaults(config_path)

    in_path = ui.require_input("input_file")
    h_f = ui.optional_param("h_f", defaults.get("IgG1/4 HC-F", ""))
    h_r = ui.optional_param("h_r", defaults.get("IgG1 HC-R", defaults.get("IgG4 HC-R", "")))
    l_f = ui.optional_param("l_f", defaults.get("kappa LC-F", defaults.get("lambda LC-F", "")))
    l_r = ui.optional_param("l_r", defaults.get("kappa LC-R", defaults.get("lambda LC-R", "")))
    cell_line = ui.optional_param("cell_line", "CHO")

    if not h_f or not h_r or not l_f or not l_r:
        ui.error("同源臂参数不完整，请在前端填写 h_f/h_r/l_f/l_r。")

    save_defaults(defaults, config_path=config_path)

    return {
        "in_path": in_path,
        "h_f": h_f,
        "h_r": h_r,
        "l_f": l_f,
        "l_r": l_r,
        "parent": None,
        "cell_line": cell_line,
    }

# 示例用法
def main():
    inputs = get_inputs()
    process_excel_advanced(
        inputs['in_path'],
        inputs['h_f'],
        inputs['h_r'],
        inputs['l_f'],
        inputs['l_r'],
        organism=inputs['cell_line'],
        parent=inputs['parent'],
    )

    return

# 用法示例
if __name__ == '__main__':
    main()
