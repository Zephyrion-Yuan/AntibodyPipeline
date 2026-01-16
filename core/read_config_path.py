from pathlib import Path
import sys, os

def get_app_dir() -> Path:
    """应用“主目录”：
    - 打包后：exe 所在目录
    - 源码环境：gen_seq.py 的父级（你的项目根）
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # PyInstaller onefile 环境
        return Path(sys.executable).resolve().parent
    else:
        # 源码运行：gen_seq.py 在 scripts/ 下，返回上一级当作项目根
        return Path(__file__).resolve().parent.parent

def get_meipass_dir() -> Path | None:
    """PyInstaller 临时目录（如果有）"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return None

def find_config_path(rel_in_config: str) -> Path:
    """优先寻找 exe 同目录的 config/<file>，其次 _MEI…/config/<file>，最后源码根目录的 config/<file>。"""
    app_dir = get_app_dir()
    # 1) exe 同目录的 config
    p1 = app_dir / "config" / rel_in_config
    if p1.exists():
        return p1

    # 2) PyInstaller 临时目录（如果 add-data 过）
    mei = get_meipass_dir()
    if mei:
        p2 = mei / "config" / rel_in_config
        if p2.exists():
            return p2

    # 3) 源码环境的 config（便于未打包调试）
    src = Path(__file__).resolve().parent.parent / "config" / rel_in_config
    if src.exists():
        return src

    # 都找不到就报错，提示去哪里放文件
    raise FileNotFoundError(
        f"找不到配置文件：config/{rel_in_config}\n"
        f"请将其放在以下任一位置：\n"
        f"  1) {app_dir / 'config' / rel_in_config}\n"
        + (f"  2) {mei / 'config' / rel_in_config}\n" if mei else "")
    )
