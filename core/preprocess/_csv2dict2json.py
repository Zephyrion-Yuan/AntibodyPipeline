import json

# 原始数据粘贴到字符串中
data = """
TTT	F	0.47
TTC	F	0.53
TTA	L	0.07
TTG	L	0.14
TAT	Y	0.44
TAC	Y	0.56
TAA	*	0.26
TAG	*	0.22
CTT	L	0.13
CTC	L	0.19
CTA	L	0.08
CTG	L	0.39
CAT	H	0.44
CAC	H	0.56
CAA	Q	0.24
CAG	Q	0.76
ATT	I	0.35
ATC	I	0.51
ATA	I	0.14
ATG	M	1
AAT	N	0.45
AAC	N	0.55
AAA	K	0.39
AAG	K	0.61
GTT	V	0.18
GTC	V	0.24
GTA	V	0.12
GTG	V	0.46
GAT	D	0.47
GAC	D	0.53
GAA	E	0.41
GAG	E	0.59
TCT	S	0.22
TCC	S	0.22
TCA	S	0.14
TCG	S	0.05
TGT	C	0.47
TGC	C	0.53
TGA	*	0.53
TGG	W	1
CCT	P	0.31
CCC	P	0.32
CCA	P	0.29
CCG	P	0.08
CGT	R	0.11
CGC	R	0.18
CGA	R	0.14
CGG	R	0.19
ACT	T	0.26
ACC	T	0.37
ACA	T	0.29
ACG	T	0.08
AGT	S	0.15
AGC	S	0.22
AGA	R	0.19
AGG	R	0.19
GCT	A	0.32
GCC	A	0.37
GCA	A	0.23
GCG	A	0.07
GGT	G	0.2
GGC	G	0.34
GGA	G	0.25
GGG	G	0.21
"""

result = {}

for line in data.strip().split('\n'):
    codon, aa, freq = line.strip().split('\t')
    if aa not in result:
        result[aa] = {}
    result[aa][codon] = float(freq)

# 导出到json文件
with open('codon_table.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
