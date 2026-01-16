from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class ActionField:
    key: str
    label: str
    kind: str
    required: bool = True
    options: Optional[List[str]] = None
    help_text: Optional[str] = None


@dataclass(frozen=True)
class Action:
    """可执行的功能模块定义。"""

    action_id: str
    label: str
    description: str
    entrypoint: str
    inputs: List[ActionField] = field(default_factory=list)
    params: List[ActionField] = field(default_factory=list)
    dialog_order: List[str] = field(default_factory=list)

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
        inputs=[
            ActionField(key="input_file", label="输入xlsx文件", kind="file"),
        ],
        params=[
            ActionField(
                key="cell_line",
                label="转染细胞系",
                kind="select",
                options=["CHO", "HEK293"],
                help_text="用于密码子优化模式选择",
            ),
            ActionField(key="h_f", label="IgG1/4 HC-F", kind="text"),
            ActionField(key="h_r", label="IgG1 HC-R 或 IgG4 HC-R", kind="text"),
            ActionField(key="l_f", label="kappa 或 lambda LC-F", kind="text"),
            ActionField(key="l_r", label="kappa 或 lambda LC-R", kind="text"),
        ],
    ),
    Action(
        action_id="receive_arm_conc_norm",
        label="根据片段浓度均一化",
        description="根据片段浓度生成工作站移液指令。",
        entrypoint="scripts.receive_arm_conc_norm.main",
        inputs=[
            ActionField(key="plate_file", label="样本布局表", kind="file"),
            ActionField(key="conc_file", label="浓度数据表", kind="file"),
        ],
        params=[
            ActionField(key="target_conc", label="目标浓度(ng/μl)", kind="number"),
            ActionField(key="volume", label="目标体积(μl)", kind="number"),
        ],
    ),
    Action(
        action_id="semi_clone_seq",
        label="生成涂板&挑单克隆&送测的布局表",
        description="将96孔布局转换为涂板和送测布局。",
        entrypoint="scripts.semi_clone_seq_5.main",
        inputs=[
            ActionField(key="input_file", label="96孔布局xlsx", kind="file"),
        ],
    ),
    Action(
        action_id="plasmid_seq_align",
        label="质粒测序结果自动比对",
        description="自动比对测序文件与参考序列。",
        entrypoint="scripts.plasmid_seq_align.main",
        inputs=[
            ActionField(key="reference_file", label="参考序列文件", kind="file"),
            ActionField(key="sequence_dir", label="测序目录", kind="directory"),
        ],
    ),
    Action(
        action_id="replace_correct_clones",
        label="替换正确的单克隆布局",
        description="使用比对结果修正96孔布局表。",
        entrypoint="scripts.replace_correct_clones.main",
        inputs=[
            ActionField(key="csv_file", label="比对CSV", kind="file"),
            ActionField(key="xlsx_files", label="待替换布局表", kind="files"),
        ],
    ),
    Action(
        action_id="germ_cherry_transfer",
        label="转移&排序比对正确的样本菌液",
        description="基于比对正确的样本生成cherrypick布局。",
        entrypoint="scripts.germ_cherry_transfer.main",
        inputs=[
            ActionField(key="xlsx_files", label="菌液布局表", kind="files"),
            ActionField(key="txt_files", label="匹配样本txt", kind="files"),
        ],
    ),
    Action(
        action_id="plasmid_save_cherry_transfer",
        label="保存比对正确的返测质粒",
        description="生成返测质粒的转移信息。",
        entrypoint="scripts.plasmid_save_cherry_transfer.main",
        inputs=[
            ActionField(key="xlsx_files", label="质粒布局表", kind="files"),
            ActionField(key="txt_files", label="匹配样本txt", kind="files"),
        ],
        params=[
            ActionField(
                key="combine_mode",
                label="混板规则",
                kind="select",
                options=["auto", "split", "mixed"],
                help_text="auto为默认判断，split为强制分板，mixed为强制混板",
            )
        ],
    ),
    Action(
        action_id="plasmid_conc",
        label="根据Qbit计算96孔质粒的浓度",
        description="根据Qbit数据生成浓度表。",
        entrypoint="scripts.plasmid_conc.main",
        inputs=[
            ActionField(key="plate_file", label="ELI plate布局", kind="file"),
            ActionField(key="asc_files", label="吸光度asc文件", kind="files"),
        ],
        params=[
            ActionField(key="a", label="标曲系数", kind="number"),
            ActionField(key="b", label="标曲分母", kind="number"),
            ActionField(key="c", label="标曲偏置", kind="number"),
            ActionField(key="scale", label="缩放因子", kind="number"),
            ActionField(key="m", label="标曲分母m", kind="number"),
        ],
    ),
    Action(
        action_id="plasmid_mix",
        label="匹配重链质粒&轻链质粒并转染",
        description="自动匹配重轻链质粒用于转染。",
        entrypoint="scripts.plasmid_mix.main",
        inputs=[
            ActionField(key="plates_file", label="布局表", kind="file"),
            ActionField(key="conc_file", label="浓度表", kind="file"),
            ActionField(key="pair_file", label="配对表", kind="file"),
        ],
    ),
    Action(
        action_id="conc_norm",
        label="根据BCA计算抗体浓度并均一化",
        description="根据BCA结果计算抗体浓度。",
        entrypoint="scripts.conc_norm.main",
        inputs=[
            ActionField(key="plate_file", label="样本ELI布局", kind="file"),
            ActionField(key="conc_file", label="吸光度asc", kind="file"),
        ],
        params=[
            ActionField(key="a", label="标曲系数", kind="number"),
            ActionField(key="b", label="标曲分母", kind="number"),
            ActionField(key="c", label="标曲偏置", kind="number"),
            ActionField(key="scale", label="缩放因子", kind="number"),
            ActionField(key="conc", label="目标浓度(mg/ml)", kind="number"),
            ActionField(key="volume", label="目标体积(μl)", kind="number"),
        ],
    ),
    Action(
        action_id="xlsx2fasta",
        label="将xlsx格式核酸序列转为fasta",
        description="将Excel序列转换为FASTA文件。",
        entrypoint="scripts.xlsx2fasta.main",
        inputs=[
            ActionField(key="input_file", label="输入xlsx", kind="file"),
        ],
    ),
    Action(
        action_id="separate_primer_synthesis_tables",
        label="分离合成引物返样表",
        description="拆分引物返样表为布局和浓度表。",
        entrypoint="scripts.separate_primer_synthesis_tables.main",
        inputs=[
            ActionField(key="input_file", label="引物返样表", kind="file"),
        ],
    ),
    Action(
        action_id="query_samples_and_highlights",
        label="查询并高亮样本",
        description="在Excel中高亮指定样本。",
        entrypoint="scripts.query_samples_and_highlights.main",
        inputs=[
            ActionField(key="txt_file", label="样本txt", kind="file"),
            ActionField(key="xlsx_file", label="待检索xlsx", kind="file"),
        ],
    ),
    Action(
        action_id="xlsxrealign",
        label="将xlsx的96*1数据转为布局表",
        description="将96x1数据转换成布局表。",
        entrypoint="scripts.xlsxrealign.main",
        inputs=[
            ActionField(key="input_file", label="96行数据xlsx", kind="file"),
        ],
    ),
    Action(
        action_id="translate_to_AA",
        label="将序列翻译为氨基酸",
        description="将核酸序列翻译为氨基酸。",
        entrypoint="scripts.translate_to_AA.main",
        inputs=[
            ActionField(key="input_file", label="序列xlsx", kind="file"),
        ],
    ),
    Action(
        action_id="move_files",
        label="移动子目录所有文件到母目录",
        description="整理目录结构，归集子目录文件。",
        entrypoint="scripts.move_files.main",
        inputs=[
            ActionField(key="parent_dir", label="母目录", kind="directory"),
        ],
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
