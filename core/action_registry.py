from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Callable, Dict, List


@dataclass(frozen=True)
class Action:
    """可执行的功能模块定义。"""

    action_id: str
    label: str
    description: str
    entrypoint: str

    def load(self) -> Callable[[], None]:
        """按需导入模块，避免启动时加载所有脚本。"""
        module_path, func_name = self.entrypoint.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, func_name)

    def run(self) -> None:
        """执行对应脚本入口。"""
        self.load()()


_ACTIONS: List[Action] = [
    Action(
        action_id="gen_seq",
        label="翻译优化密码子&加同源臂",
        description="输入抗体序列，输出优化后的基因序列和配对信息。",
        entrypoint="scripts.gen_seq_auto_detect_chain_classify_report.main",
    ),
    Action(
        action_id="receive_arm_conc_norm",
        label="根据片段浓度均一化",
        description="根据片段浓度生成工作站移液指令。",
        entrypoint="scripts.receive_arm_conc_norm.main",
    ),
    Action(
        action_id="semi_clone_seq",
        label="生成涂板&挑单克隆&送测的布局表",
        description="将96孔布局转换为涂板和送测布局。",
        entrypoint="scripts.semi_clone_seq_5.main",
    ),
    Action(
        action_id="plasmid_seq_align",
        label="质粒测序结果自动比对",
        description="自动比对测序文件与参考序列。",
        entrypoint="scripts.plasmid_seq_align.main",
    ),
    Action(
        action_id="replace_correct_clones",
        label="替换正确的单克隆布局",
        description="使用比对结果修正96孔布局表。",
        entrypoint="scripts.replace_correct_clones.main",
    ),
    Action(
        action_id="germ_cherry_transfer",
        label="转移&排序比对正确的样本菌液",
        description="基于比对正确的样本生成cherrypick布局。",
        entrypoint="scripts.germ_cherry_transfer.main",
    ),
    Action(
        action_id="plasmid_save_cherry_transfer",
        label="保存比对正确的返测质粒",
        description="生成返测质粒的转移信息。",
        entrypoint="scripts.plasmid_save_cherry_transfer.main",
    ),
    Action(
        action_id="plasmid_conc",
        label="根据Qbit计算96孔质粒的浓度",
        description="根据Qbit数据生成浓度表。",
        entrypoint="scripts.plasmid_conc.main",
    ),
    Action(
        action_id="plasmid_mix",
        label="匹配重链质粒&轻链质粒并转染",
        description="自动匹配重轻链质粒用于转染。",
        entrypoint="scripts.plasmid_mix.main",
    ),
    Action(
        action_id="conc_norm",
        label="根据BCA计算抗体浓度并均一化",
        description="根据BCA结果计算抗体浓度。",
        entrypoint="scripts.conc_norm.main",
    ),
    Action(
        action_id="xlsx2fasta",
        label="将xlsx格式核酸序列转为fasta",
        description="将Excel序列转换为FASTA文件。",
        entrypoint="scripts.xlsx2fasta.main",
    ),
    Action(
        action_id="separate_primer_synthesis_tables",
        label="分离合成引物返样表",
        description="拆分引物返样表为布局和浓度表。",
        entrypoint="scripts.separate_primer_synthesis_tables.main",
    ),
    Action(
        action_id="query_samples_and_highlights",
        label="查询并高亮样本",
        description="在Excel中高亮指定样本。",
        entrypoint="scripts.query_samples_and_highlights.main",
    ),
    Action(
        action_id="xlsxrealign",
        label="将xlsx的96*1数据转为布局表",
        description="将96x1数据转换成布局表。",
        entrypoint="scripts.xlsxrealign.main",
    ),
    Action(
        action_id="translate_to_AA",
        label="将序列翻译为氨基酸",
        description="将核酸序列翻译为氨基酸。",
        entrypoint="scripts.translate_to_AA.main",
    ),
    Action(
        action_id="move_files",
        label="移动子目录所有文件到母目录",
        description="整理目录结构，归集子目录文件。",
        entrypoint="scripts.move_files.main",
    ),
]


def list_actions() -> List[Action]:
    """返回所有动作定义。"""
    return list(_ACTIONS)


def get_action_map() -> Dict[str, Action]:
    """构建id到动作的映射，供快速索引。"""
    return {action.action_id: action for action in _ACTIONS}


def run_action(action_id: str) -> None:
    """根据动作ID执行脚本。"""
    actions = get_action_map()
    action = actions.get(action_id)
    if not action:
        raise KeyError(f"Unknown action_id: {action_id}")
    action.run()
