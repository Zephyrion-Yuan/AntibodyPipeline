import pandas as pd
from pathlib import Path

from core.ui_inputs import UIContext


def main():
    ui = UIContext.from_env()
    input_file = ui.require_input("input_file")
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

    ui.info(result_msg)

if __name__ == '__main__':
    main()
