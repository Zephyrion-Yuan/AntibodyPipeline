import pandas as pd

def xlsx_to_fasta(xlsx_path, fasta_path, name_col=0, seq_col=1):
    # 读取 Excel 文件，默认无表头
    df = pd.read_excel(xlsx_path, header=None)
    
    # 打开输出 FASTA 文件
    with open(fasta_path, 'w') as out_f:
        for idx, row in df.iterrows():
            name = str(row[name_col]).strip()
            seq = str(row[seq_col]).strip().upper()
            if not name or not seq:
                continue  # 跳过空行
            out_f.write(f'>{name}\n')
            # 将序列按 60 字母分行输出（可选）
            for i in range(0, len(seq), 60):
                out_f.write(seq[i:i+60] + '\n')

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("用法：python xlsx2fasta.py 输入.xlsx 输出.fasta")
    else:
        xlsx_to_fasta(sys.argv[1], sys.argv[2])
