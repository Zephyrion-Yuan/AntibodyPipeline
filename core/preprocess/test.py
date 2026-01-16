
# 重链数量为H，轻链数量为L，如果H + L % 96 < 48，则分开，否则不分开。不分开的方式为：重链先填充混合板，轻链再填充混合板，同时，混合板中的重链和轻链都是升序排序后最后一部分的样本编号。
def assign_plate_positions(processed_ab):
    n = len(processed_ab)
    h_count = 0
    for v in processed_ab:
        if v.endswith('H'):
            h_count += 1
        else:
            break
    l_count = n - h_count

    if h_count % 96 + l_count % 96 > 96:
        dest_positions = []
        dest_plate = []
        for i in range(n):
            if i < h_count:
                h_pos_idx = i % 96 + 1
                dest_positions.append(h_pos_idx)
                h_plate_idx = i // 96 + 1
                dest_plate.append(f'cherry_H_{h_plate_idx}')
            else:
                cnt = i - h_count
                l_pos_idx = cnt % 96 + 1
                dest_positions.append(l_pos_idx)
                l_plate_idx = cnt // 96 + 1
                dest_plate.append(f'cherry_L_{l_plate_idx}')
        return dest_positions, dest_plate
    else:
        dest_positions = []
        dest_plate = []
        mix_plate_idx = h_count // 96 + 1
        mix_plate_l_start = h_count % 96
        l_mix_start = h_count + (l_count // 96) * 96
        for i in range(h_count):
            h_pos_idx = i % 96 + 1
            dest_positions.append(h_pos_idx)
            h_plate_idx = i // 96 + 1
            dest_plate.append(f'cherry_H_{h_plate_idx}')
        for i in range(h_count, l_mix_start):
            cnt = i - h_count
            l_pos_idx = cnt % 96 + 1
            dest_positions.append(l_pos_idx)
            l_plate_idx = cnt // 96 + 1
            dest_plate.append(f'cherry_L_{l_plate_idx}')
        for i in range(l_mix_start, n):
            l_pos_idx = i - l_mix_start + mix_plate_l_start + 1
            dest_positions.append(l_pos_idx)
            dest_plate.append(f'cherry_H_{mix_plate_idx}')
        return dest_positions, dest_plate

def print_assignment(processed_ab):
    pos, plate = assign_plate_positions(processed_ab)
    for ab, p, pl in zip(processed_ab, pos, plate):
        print(f"{ab:10}  {p:3}  {pl}")

def test():
    # # 90H + 50L = 140，应该分开
    # processed_ab = [f'Ab{i}-H' for i in range(90)] + [f'Ab{i}-L' for i in range(50)]
    # print("Test1: 90H+50L 分开")
    # print_assignment(processed_ab)

    # # 60H + 90L = 150，最后一个H板混合
    # processed_ab = [f'Ab{i}-H' for i in range(60)] + [f'Ab{i}-L' for i in range(90)]
    # print("\nTest2: 60H+90L 不分开，混合板")
    # print_assignment(processed_ab)

    # 106H + 106L = 212，最后一个H板混合
    processed_ab = [f'Ab{i}-H' for i in range(106)] + [f'Ab{i}-L' for i in range(106)]
    print("\nTest3: 106H+106L 不分开")
    print_assignment(processed_ab)

    # # 110H + 90L = 200, (200%96=8) <48，分开
    # processed_ab = [f'Ab{i}-H' for i in range(110)] + [f'Ab{i}-L' for i in range(90)]
    # print("\nTest4: 110H+90L 分开")
    # print_assignment(processed_ab)

    # 110H + 90L = 200, 测试分板、位置编号连续性
    assert len(assign_plate_positions(processed_ab)[0]) == len(processed_ab)

test()