import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

def move_subdir_files_to_parent(parent_dir):
    """
    将指定母目录下所有子目录（包括嵌套子目录）中的文件移动到母目录
    
    参数:
        parent_dir: 母目录的路径（绝对路径或相对路径）
    """
    # 确保母目录存在
    if not os.path.isdir(parent_dir):
        raise ValueError(f"目录不存在: {parent_dir}")
    
    # 遍历母目录下的所有条目（递归处理所有子目录）
    for root, dirs, files in os.walk(parent_dir):
        # 跳过母目录本身（只处理子目录）
        if root == parent_dir:
            continue
        
        # 处理当前子目录中的所有文件
        for file in files:
            # 源文件路径（子目录中的文件）
            src_path = os.path.join(root, file)
            # 目标路径（母目录下的文件）
            dest_path = os.path.join(parent_dir, file)
            
            # 若目标文件已存在，添加序号后缀避免覆盖（如 "a.txt" → "a_1.txt"）
            counter = 1
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(file)
                dest_path = os.path.join(parent_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            # 移动文件
            shutil.move(src_path, dest_path)
            print(f"移动成功: {src_path} → {dest_path}")
    
    # 可选：删除所有空的子目录（包括嵌套的空目录）
    # 从最深层的子目录开始删除，避免父目录先被删除导致子目录无法访问
    for root, dirs, files in os.walk(parent_dir, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):  # 检查目录是否为空
                os.rmdir(dir_path)
                print(f"删除空目录: {dir_path}")


def main():
    # 获取用户选择的母目录
    root = tk.Tk()
    root.withdraw()
    parent_dir = filedialog.askdirectory(title="请选择母目录")
    
    if parent_dir:
        move_subdir_files_to_parent(parent_dir)
        messagebox.showinfo("完成", "文件已移动到母目录。")
    else:
        messagebox.showwarning("取消", "未选择母目录。")
    root.destroy()
    return

if __name__ == "__main__":
    main()