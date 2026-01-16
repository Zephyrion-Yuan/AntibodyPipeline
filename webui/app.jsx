const { useEffect, useState } = React;

const STATUS_LABELS = {
  todo: "待开始",
  running: "进行中",
  done: "已完成",
  blocked: "阻塞",
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
    gantt: [
      { step: "gene", start: 1, end: 2, status: "done" },
      { step: "primer", start: 3, end: 3.5, status: "done" },
      { step: "clone", start: 4, end: 6, status: "running" },
    ],
    nodes: [
      { id: "gene", label: "基因合成", x: 120, y: 140 },
      { id: "primer", label: "引物浓度均一化", x: 320, y: 110 },
      { id: "clone", label: "转化涂板&挑单克隆", x: 520, y: 180 },
    ],
    links: [
      ["gene", "primer"],
      ["primer", "clone"],
    ],
  },
  {
    id: "B-2025-02",
    owner: "项目B",
    samples: 96,
    gantt: [],
    nodes: [],
    links: [],
  },
  {
    id: "B-2025-03",
    owner: "复做批次",
    samples: 128,
    gantt: [
      { step: "gene", start: 1, end: 2, status: "done" },
      { step: "primer", start: 2.5, end: 3.5, status: "done" },
      { step: "clone", start: 4, end: 5, status: "done" },
      { step: "seq", start: 5.5, end: 7, status: "running" },
    ],
    nodes: [
      { id: "gene", label: "基因合成", x: 140, y: 150 },
      { id: "primer", label: "引物浓度均一化", x: 320, y: 100 },
      { id: "clone", label: "转化涂板&挑单克隆", x: 520, y: 160 },
      { id: "seq", label: "菌液测序", x: 700, y: 120 },
    ],
    links: [
      ["gene", "primer"],
      ["primer", "clone"],
      ["clone", "seq"],
    ],
  },
];

function Header() {
  return (
    <header className="header">
      <div>
        <p className="header__eyebrow">AntibodyPipeline</p>
        <h1>批次数据库</h1>
        <p className="header__subtitle">
          Minimal · Notion Database · 默认甘特图视图
        </p>
      </div>
      <div className="header__badge">Local UI</div>
    </header>
  );
}

function GanttRow({ row }) {
  const label = SOP_STEPS.find((step) => step.key === row.step)?.label || row.step;
  return (
    <div className="gantt-row">
      <span className="gantt-row__label">{label}</span>
      <div className="gantt-row__bar">
        <div
          className={`gantt-bar gantt-bar--${row.status}`}
          style={{
            left: `${row.start * 10}%`,
            width: `${(row.end - row.start) * 10}%`,
          }}
        />
      </div>
    </div>
  );
}

function BatchList({ batches, selectedId, onSelect }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h2>批次数据库</h2>
        <p>以批次为单位组织，默认视图为甘特图。</p>
      </div>
      <div className="batch-table">
        <div className="batch-table__row batch-table__row--head">
          <span>批次</span>
          <span>项目</span>
          <span>样本数</span>
          <span>状态</span>
        </div>
        {batches.map((batch) => {
          const status = batch.gantt.length ? "running" : "todo";
          return (
            <button
              type="button"
              key={batch.id}
              className={`batch-table__row batch-table__row--clickable ${
                selectedId === batch.id ? "is-active" : ""
              }`}
              onClick={() => onSelect(batch.id)}
            >
              <span className="batch-table__id">{batch.id}</span>
              <span>{batch.owner}</span>
              <span>{batch.samples}</span>
              <span className={`status-pill status-pill--${status}`}>
                {STATUS_LABELS[status]}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function BatchGantt({ batch }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h2>甘特图视图</h2>
        <p>仅展示已处理的环节。</p>
      </div>
      <div className="gantt">
        {batch.gantt.length ? (
          batch.gantt.map((row) => <GanttRow key={row.step} row={row} />)
        ) : (
          <div className="empty-state">当前批次暂无已处理环节。</div>
        )}
      </div>
    </section>
  );
}

function BatchCanvas({ batch }) {
  const canvasRef = React.useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = "#d8dee8";
    ctx.lineWidth = 1.5;
    batch.links.forEach(([from, to]) => {
      const start = batch.nodes.find((node) => node.id === from);
      const end = batch.nodes.find((node) => node.id === to);
      if (!start || !end) return;
      ctx.beginPath();
      ctx.moveTo(start.x + 70, start.y);
      ctx.quadraticCurveTo((start.x + end.x) / 2, start.y - 60, end.x - 70, end.y);
      ctx.stroke();
    });

    batch.nodes.forEach((node) => {
      ctx.fillStyle = "#ffffff";
      ctx.strokeStyle = "#1b1f2a";
      ctx.lineWidth = 1;
      ctx.beginPath();
      const radius = 12;
      const width = 140;
      const height = 48;
      const left = node.x - width / 2;
      const top = node.y - height / 2;
      ctx.moveTo(left + radius, top);
      ctx.lineTo(left + width - radius, top);
      ctx.quadraticCurveTo(left + width, top, left + width, top + radius);
      ctx.lineTo(left + width, top + height - radius);
      ctx.quadraticCurveTo(left + width, top + height, left + width - radius, top + height);
      ctx.lineTo(left + radius, top + height);
      ctx.quadraticCurveTo(left, top + height, left, top + height - radius);
      ctx.lineTo(left, top + radius);
      ctx.quadraticCurveTo(left, top, left + radius, top);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#1b1f2a";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(node.label, node.x, node.y + 4);
    });
  }, [batch]);

  return (
    <section className="panel">
      <div className="panel__header">
        <h2>流程画布</h2>
        <p>仅展示已处理环节的 96 孔板节点。</p>
      </div>
      <div className="canvas-wrapper">
        <canvas ref={canvasRef} width="880" height="320" />
      </div>
    </section>
  );
}

function IncrementalUpload({ batchId }) {
  const [file, setFile] = useState(null);
  const [confirmed, setConfirmed] = useState(false);

  return (
    <section className="panel">
      <div className="panel__header">
        <h2>增量上传</h2>
        <p>仅上传新信息，旧孔板/浓度/匹配数据无需重复上传。</p>
      </div>
      <div className="incremental">
        <label className="field">
          <span>增量文件</span>
          <input type="file" onChange={(event) => setFile(event.target.files?.[0])} />
          <em>{file ? `已选择: ${file.name}` : "支持拖拽或点击选择文件"}</em>
        </label>
        <label className="toggle">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(event) => setConfirmed(event.target.checked)}
          />
          手动确认后写入新节点
        </label>
        <button type="button" className="action-card__cta" disabled={!file || !confirmed}>
          提交到 {batchId}
        </button>
      </div>
    </section>
  );
}

function App() {
  const [selectedId, setSelectedId] = useState(SAMPLE_BATCHES[0].id);
  const selectedBatch = SAMPLE_BATCHES.find((batch) => batch.id === selectedId);

  return (
    <div className="app">
      <Header />
      <div className="layout">
        <div className="layout__left">
          <BatchList
            batches={SAMPLE_BATCHES}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </div>
        <div className="layout__right">
          <BatchGantt batch={selectedBatch} />
          <BatchCanvas batch={selectedBatch} />
          <IncrementalUpload batchId={selectedBatch.id} />
        </div>
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
