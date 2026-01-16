const { useEffect, useMemo, useState } = React;

const STATUS_LABELS = {
  todo: "待开始",
  running: "进行中",
  done: "已完成",
  blocked: "阻塞",
};

const STATUS_STYLES = {
  todo: "status status--todo",
  running: "status status--running",
  done: "status status--done",
  blocked: "status status--blocked",
};

const SOP_STEPS = [
  { key: "gene", label: "基因合成" },
  { key: "primer", label: "引物浓度均一化" },
  { key: "clone", label: "转化涂板&挑单克隆" },
  { key: "seq", label: "菌液测序" },
  { key: "plasmid", label: "质粒&菌液cherrypick" },
  { key: "plasmid_conc", label: "质粒浓度" },
  { key: "transfection", label: "转染表达" },
  { key: "purify", label: "纯化和蛋白浓度" },
];

const SAMPLE_BATCHES = [
  {
    id: "B-2025-01",
    owner: "项目A",
    samples: 192,
    status: "running",
    stepProgress: {
      gene: "done",
      primer: "done",
      clone: "running",
      seq: "todo",
      plasmid: "todo",
      plasmid_conc: "todo",
      transfection: "todo",
      purify: "todo",
    },
  },
  {
    id: "B-2025-02",
    owner: "项目B",
    samples: 96,
    status: "todo",
    stepProgress: {
      gene: "todo",
      primer: "todo",
      clone: "todo",
      seq: "todo",
      plasmid: "todo",
      plasmid_conc: "todo",
      transfection: "todo",
      purify: "todo",
    },
  },
  {
    id: "B-2025-03",
    owner: "复做批次",
    samples: 128,
    status: "running",
    stepProgress: {
      gene: "done",
      primer: "done",
      clone: "done",
      seq: "running",
      plasmid: "todo",
      plasmid_conc: "todo",
      transfection: "todo",
      purify: "todo",
    },
  },
];

function Header() {
  return (
    <header className="header">
      <div>
        <p className="header__eyebrow">AntibodyPipeline</p>
        <h1>抗体自动化工具箱</h1>
        <p className="header__subtitle">
          单机运行 · 96孔板流程管理 · 任务脚本入口统一管理
        </p>
      </div>
      <div className="header__badge">v2 Web UI</div>
    </header>
  );
}

function ActionRunner({ action, onRun }) {
  const [files, setFiles] = useState({});
  const [params, setParams] = useState({});

  const handleFileChange = (key, event) => {
    const selected = Array.from(event.target.files || []);
    setFiles((prev) => ({ ...prev, [key]: selected }));
  };

  const handleParamChange = (key, value) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    onRun(action.id, { files, params });
  };

  return (
    <form className="action-card" onSubmit={handleSubmit}>
      <div className="action-card__title">{action.label}</div>
      <div className="action-card__desc">{action.description}</div>
      <div className="action-card__fields">
        {action.inputs.map((field) => (
          <label key={field.key} className="field">
            <span>{field.label}</span>
            <input
              type="file"
              multiple={field.kind === "files" || field.kind === "directory"}
              webkitdirectory={field.kind === "directory" ? "true" : undefined}
              onChange={(event) => handleFileChange(field.key, event)}
              required={field.required}
            />
            <em>支持拖拽或点击选择文件</em>
          </label>
        ))}
        {action.params.map((field) => (
          <label key={field.key} className="field">
            <span>{field.label}</span>
            {field.kind === "select" ? (
              <select
                value={params[field.key] || ""}
                onChange={(event) => handleParamChange(field.key, event.target.value)}
                required={field.required}
              >
                <option value="">请选择</option>
                {(field.options || []).map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={field.kind === "number" ? "number" : "text"}
                value={params[field.key] || ""}
                onChange={(event) => handleParamChange(field.key, event.target.value)}
                required={field.required}
              />
            )}
            {field.help_text && <em>{field.help_text}</em>}
          </label>
        ))}
      </div>
      <button type="submit" className="action-card__cta">
        ▶ 运行脚本
      </button>
    </form>
  );
}

function ActionList({ actions, onRun }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h2>功能模块</h2>
        <p>按SOP顺序统一入口，脚本执行在本机环境。</p>
      </div>
      <div className="action-grid">
        {actions.map((action) => (
          <ActionRunner key={action.id} action={action} onRun={onRun} />
        ))}
      </div>
    </section>
  );
}

function BatchProgress({ batches }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h2>批次进度总览</h2>
        <p>支持96-384样本批次，可选择样本复做并追踪历史。</p>
      </div>
      <div className="batch-table">
        <div className="batch-table__row batch-table__row--head">
          <span>批次</span>
          <span>项目</span>
          <span>样本数</span>
          <span>进度</span>
          <span>流程</span>
        </div>
        {batches.map((batch) => (
          <div key={batch.id} className="batch-table__row">
            <span className="batch-table__id">{batch.id}</span>
            <span>{batch.owner}</span>
            <span>{batch.samples}</span>
            <span className={STATUS_STYLES[batch.status]}>
              {STATUS_LABELS[batch.status]}
            </span>
            <div className="timeline">
              {SOP_STEPS.map((step) => (
                <div
                  key={step.key}
                  className={`timeline__step timeline__step--${batch.stepProgress[step.key]}`}
                  title={`${step.label}：${STATUS_LABELS[batch.stepProgress[step.key]]}`}
                >
                  <span>{step.label}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function PlateEditorPreview() {
  const cells = useMemo(() => {
    const rows = "ABCDEFGH".split("");
    const cols = Array.from({ length: 12 }, (_, idx) => idx + 1);
    return rows.flatMap((row) =>
      cols.map((col) => ({
        id: `${row}${col}`,
        sample: `${row}${col}-S`,
      }))
    );
  }, []);

  return (
    <section className="panel">
      <div className="panel__header">
        <h2>96孔板编辑预览</h2>
        <p>支持每个环节修改样本信息，系统保留历史版本。</p>
      </div>
      <div className="plate-grid">
        {cells.map((cell) => (
          <div key={cell.id} className="plate-cell">
            <strong>{cell.id}</strong>
            <span>{cell.sample}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function App() {
  const [actions, setActions] = useState([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("/api/actions")
      .then((res) => res.json())
      .then((data) => setActions(data.actions || []))
      .catch(() => setActions([]));
  }, []);

  const handleRun = (id, payload) => {
    setMessage(`已提交：${id}`);
    const formData = new FormData();
    Object.entries(payload.files || {}).forEach(([key, fileList]) => {
      (fileList || []).forEach((file) => formData.append(key, file));
    });
    formData.append("params", JSON.stringify(payload.params || {}));
    fetch(`/api/actions/${id}/run`, { method: "POST", body: formData }).catch(
      () => {
        setMessage("调用失败，请确认后端已启动。");
      }
    );
  };

  return (
    <div className="app">
      <Header />
      {message && <div className="banner">{message}</div>}
      <ActionList actions={actions} onRun={handleRun} />
      <BatchProgress batches={SAMPLE_BATCHES} />
      <PlateEditorPreview />
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
