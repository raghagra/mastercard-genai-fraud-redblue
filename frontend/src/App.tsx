import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, Bot, Check, Columns3, Database, Play, RefreshCw, Search, ShieldCheck, Sparkles, Waves, X } from "lucide-react";
import { API_URL, api } from "./api";
import type { AttackCard, Iteration, Provider } from "./types";

type View = "overview" | "catalog" | "loop" | "portfolio" | "providers";
const nav: { id: View; label: string; icon: typeof Activity }[] = [
  { id: "overview", label: "Mission control", icon: Activity },
  { id: "catalog", label: "Attack catalog", icon: AlertTriangle },
  { id: "loop", label: "Closed loop", icon: RefreshCw },
  { id: "portfolio", label: "Portfolio onboarding", icon: Database },
  { id: "providers", label: "GenAI gateway", icon: Bot },
];

const prettify = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
const metric = (value?: number) => value == null ? "—" : `${(value * 100).toFixed(1)}%`;

export default function App() {
  const [view, setView] = useState<View>("overview");
  const [catalog, setCatalog] = useState<AttackCard[]>([]);
  const [iterations, setIterations] = useState<Iteration[]>([]);
  const [providers, setProviders] = useState<Record<string, Provider>>({});
  const [apiOnline, setApiOnline] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function refresh() {
    try {
      const [health, attackData, loopData, providerData] = await Promise.all([
        api<{ status: string }>("/health"),
        api<{ cards: AttackCard[] }>("/attack-catalog"),
        api<{ iterations: Iteration[] }>("/loop/iterations"),
        api<{ providers: Record<string, Provider> }>("/genai/providers"),
      ]);
      setApiOnline(health.status === "ok"); setCatalog(attackData.cards); setIterations(loopData.iterations); setProviders(providerData.providers);
    } catch (error) { setApiOnline(false); setMessage(error instanceof Error ? error.message : "Cannot reach the API"); }
  }
  useEffect(() => { void refresh(); }, []);

  const buckets = useMemo(() => [...new Set(catalog.map((card) => card.bucket))], [catalog]);
  const latest = iterations.at(-1);
  const content = view === "overview" ? <Overview cards={catalog} buckets={buckets} latest={latest} onRun={async () => {
    setMessage("Running the complete red-team / blue-team iteration…");
    try { const result = await api<{ summary: { iteration_id: string } }>("/loop/run", { method: "POST", body: JSON.stringify({}) }); setMessage(`Completed ${result.summary.iteration_id}.`); await refresh(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Loop run failed"); }
  }} /> :
    view === "catalog" ? <Catalog cards={catalog} buckets={buckets} /> :
    view === "loop" ? <Loop iterations={iterations} refresh={refresh} onNotice={setMessage} /> :
    view === "portfolio" ? <Portfolio iterations={iterations} onNotice={setMessage} /> : <Gateway providers={providers} onNotice={setMessage} />;

  return <main className="app-shell">
    <aside className="sidebar"><div className="brand"><span className="brand-mark"><ShieldCheck size={21} /></span><span>sentinel<span>loop</span></span></div>
      <div className="workspace-label">RED / BLUE OPERATIONS</div>
      <nav>{nav.map((item) => { const Icon = item.icon; return <button key={item.id} className={view === item.id ? "nav-item active" : "nav-item"} onClick={() => setView(item.id)}><Icon size={17} />{item.label}</button>; })}</nav>
      <div className="sidebar-foot"><span className={apiOnline ? "status-dot online" : "status-dot"}/>{apiOnline ? "API connected" : "API unavailable"}</div>
    </aside>
    <section className="main-panel"><header><div><p className="eyebrow">GENAI PAYMENT FRAUD LAB</p><h1>{nav.find((item) => item.id === view)?.label}</h1></div><button className="ghost-button" onClick={() => void refresh()}><RefreshCw size={15}/> Refresh</button></header>
      {message && <div className="toast"><span>{message}</span><button onClick={() => setMessage(null)}>×</button></div>}
      {content}
    </section>
  </main>;
}

function Overview({ cards, buckets, latest, onRun }: { cards: AttackCard[]; buckets: string[]; latest?: Iteration; onRun: () => void }) {
  return <><section className="hero"><div><p className="eyebrow accent">CLOSED-LOOP SECURITY</p><h2>Discover. Simulate. Defend.</h2><p>Turn emerging GenAI-powered payment attacks into a continuously improving training ground for detection.</p><button className="primary-button" onClick={onRun}><Waves size={17}/> Run a loop iteration</button></div><div className="loop-diagram"><span><Sparkles/> Identify</span><i>→</i><span><Database/> Generate</span><i>→</i><span><ShieldCheck/> Defend</span><i>↺</i></div></section>
  <section className="stat-grid"><Stat label="Attack vectors" value={String(cards.length)} detail="Mapped across five fraud families"/><Stat label="Fraud families" value={String(buckets.length)} detail="Cards, identity, merchant, social & post-event"/><Stat label="Latest F1" value={metric(latest?.evaluation_overall?.f1)} detail={latest ? latest.iteration_id : "Run an iteration to measure"}/><Stat label="Loop iterations" value={String(latest ? 1 : 0)} detail={latest ? "Feedback-ready simulations" : "No run recorded"}/></section>
  <section className="two-column"><article className="panel"><div className="panel-title"><h3>Attack landscape</h3><span>{cards.length} cards</span></div><div className="bucket-list">{buckets.map((bucket) => <div className="bucket-row" key={bucket}><span className="bucket-icon"><AlertTriangle size={16}/></span><span>{prettify(bucket)}</span><strong>{cards.filter((card) => card.bucket === bucket).length}</strong></div>)}</div></article><article className="panel"><div className="panel-title"><h3>Latest defense signal</h3><span>{latest?.iteration_id ?? "Awaiting run"}</span></div>{latest ? <div className="signal"><div className="score-ring">{metric(latest.evaluation_overall.f1)}</div><div><h4>Detection performance</h4><p>Precision {metric(latest.evaluation_overall.precision)} · Recall {metric(latest.evaluation_overall.recall)}</p><p className="muted">Review generated mutations, then feed accepted refinements into the next run.</p></div></div> : <Empty text="Launch a closed-loop iteration to create a defense baseline."/>}</article></section></>;
}

function Catalog({ cards, buckets }: { cards: AttackCard[]; buckets: string[] }) { const [filter, setFilter] = useState("all"); const shown = filter === "all" ? cards : cards.filter((card) => card.bucket === filter); return <section className="panel catalog"><div className="panel-title"><div><h3>Known attack surface</h3><p>Curated, payment-grounded threats ready for simulation.</p></div><select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">All families</option>{buckets.map((bucket) => <option key={bucket} value={bucket}>{prettify(bucket)}</option>)}</select></div><div className="table-wrap"><table><thead><tr><th>Attack</th><th>Family</th><th>Channel / rail</th><th>Severity</th></tr></thead><tbody>{shown.map((card) => <tr key={card.attack_id}><td><strong>{card.attack_name}</strong><small>{card.variant_name}</small></td><td><span className="chip">{prettify(card.bucket)}</span></td><td>{card.channel}<small>{card.rail}</small></td><td><span className={`severity ${card.severity.toLowerCase()}`}>{card.severity}</span></td></tr>)}</tbody></table></div></section> }

type Job = { job_id: string; status: string; stage: string; iteration_id?: string; summary?: IterationDetail; error?: string };
type IterationDetail = Iteration & { benign_count: number; per_attack_card: number; review_source_iteration_id?: string; train_metrics: Record<string, number>; failure_summary: { false_positives: number; false_negatives: number; weak_groups: WeakGroup[] } };
type WeakGroup = { group_key: string; bucket: string; subtype: string; avg_fraud_score: number; fraud_count: number; miss_count: number };
type MutationDelta = { field: string; baseline: string | number | string[] | number[]; proposed: string | number | string[] | number[]; purpose: string };
type MutationEvidence = { evaluation_scope: string; selection_reason: string; threshold?: number; fraud_count: number; miss_count: number; recall?: number; average_fraud_score?: number; representative_records: { transaction_id: string; fraud_score: number; reason_codes: string }[] };
type Mutation = { mutation_id: string; proposed_variant_name: string; subtype: string; bucket: string; rationale: string; mutation_strategy: string[]; parameter_deltas: MutationDelta[]; provider: string; gateway_fallback?: { reason: string }; review_evidence?: MutationEvidence };
type Review = { mutation_id: string; decision: string };
type MutationImpact = { source_iteration_id: string | null; accepted_mutations: { mutation_id: string; subtype: string; proposed_variant_name: string; provider: string }[]; outcome: { source_metrics: Record<string, number>; candidate_metrics: Record<string, number>; metric_deltas: Record<string, number>; mutations_consumed: number; overlays_applied: number } | null; disclosure: string };
type ControlledExperiment = { mutation: { mutation_id: string; subtype: string; proposed_variant_name: string; parameter_deltas: MutationDelta[] }; design: { seed: number; benign_count_per_arm: number; scenarios_per_arm: number; detector: string }; baseline: { record_count: number; fraud_record_count: number; miss_count: number; metrics: Record<string, number> }; mutated: { record_count: number; fraud_record_count: number; miss_count: number; metrics: Record<string, number> }; metric_deltas: Record<string, number>; deterministic_explanation: string; disclosure: string };
type TransactionRecord = { transaction_id: string; event_time: string; amount: number; currency: string; channel: string; rail: string; merchant_category: string; label: number; attack_bucket: string; attack_subtype: string; fraud_score: number; ml_fraud_score: number; prediction: number; llm_reviewed: number; llm_provider: string; llm_semantic_risk_score: number | null; decision_engine: string; reason_codes: string[] };
type TransactionPage = { total: number; page: number; page_size: number; items: TransactionRecord[]; filters: { buckets: string[]; decision_engines: string[] } };
type TransactionDetail = { transaction: Record<string, string>; detection: Record<string, string | string[]>; entities: Record<string, Record<string, string> | null>; attack_instance: Record<string, string> | null; generation_provenance: Record<string, unknown>; decision_provenance: Record<string, unknown> };
type UsageCall = { timestamp: string; provider: string; task: string; input_tokens_estimated: number; output_tokens_estimated: number; latency_ms: number | null; fallback?: { from_provider: string; to_provider: string; reason: string } | null };
type UsageSummary = { call_count: number; input_tokens_estimated: number; output_tokens_estimated: number; latency_ms_total: number; cost_estimates: { model_key: string; provider: string; model: string; estimated_total_cost: number; currency: string }[]; calls: UsageCall[] };
const stages = ["preparing", "generating", "building_features", "training", "scoring", "evaluating", "analyzing_failures", "proposing_mutations", "completed"];
const mutationParameterDefinitions: Record<string, string> = {
  stealth_level_range: "The minimum and maximum stealth level used when generating this scenario. Higher levels intentionally make the simulated attack resemble benign payment behaviour more closely.",
  volume_range: "The minimum and maximum number of events produced for this scenario. It controls campaign volume and helps test both low-and-slow and higher-volume fraud patterns.",
  time_window_multiplier: "A multiplier for the simulated campaign duration. A value above one spreads activity across a longer window, reducing obvious velocity signals.",
  noise_level: "The amount of controlled variation added to generated records. It creates realistic edge cases while preserving the attack's core signal.",
};

function Loop({ iterations, refresh, onNotice }: { iterations: Iteration[]; refresh: () => Promise<void>; onNotice: (message: string) => void }) {
  const [selectedId, setSelectedId] = useState<string | null>(iterations.at(-1)?.iteration_id ?? null);
  const [detail, setDetail] = useState<IterationDetail | null>(null);
  const [mutationData, setMutationData] = useState<{ candidates: Mutation[]; reviews: Review[] }>({ candidates: [], reviews: [] });
  const [job, setJob] = useState<Job | null>(null);
  const [comparison, setComparison] = useState<{ metric_deltas: Record<string, number> } | null>(null);
  const [runSettings, setRunSettings] = useState({ seed: "42", benign_count: "500", per_attack_card: "1", mutation_candidate_limit: "5", review_source_iteration_id: "" });
  const [iterationPage, setIterationPage] = useState(1);
  const iterationPageSize = 6;
  const newestFirstIterations = [...iterations].reverse();
  const iterationPageCount = Math.max(1, Math.ceil(newestFirstIterations.length / iterationPageSize));
  const visibleIterations = newestFirstIterations.slice((iterationPage - 1) * iterationPageSize, iterationPage * iterationPageSize);

  useEffect(() => { if (!selectedId && iterations.length) setSelectedId(iterations.at(-1)!.iteration_id); }, [iterations, selectedId]);
  useEffect(() => { setIterationPage(1); }, [iterations.length]);
  useEffect(() => { if (selectedId) void loadDetail(selectedId); }, [selectedId]);
  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await api<Job>(`/loop/jobs/${job.job_id}`); setJob(next);
        if (next.status === "completed") { await refresh(); if (next.iteration_id) setSelectedId(next.iteration_id); onNotice(`${next.iteration_id} completed.`); }
        if (next.status === "failed") onNotice(next.error ?? "Iteration failed.");
      } catch (error) { onNotice(error instanceof Error ? error.message : "Could not read job status"); }
    }, 900);
    return () => window.clearInterval(timer);
  }, [job, refresh, onNotice]);

  async function loadDetail(iterationId: string) {
    try {
      const [summary, mutations] = await Promise.all([
        api<IterationDetail>(`/loop/iterations/${iterationId}`),
        api<{ candidates: Mutation[]; reviews: Review[] }>(`/loop/iterations/${iterationId}/mutations`),
      ]);
      setDetail(summary); setMutationData(mutations);
    } catch (error) { onNotice(error instanceof Error ? error.message : "Could not load iteration details"); }
  }
  async function startRun() {
    try {
      const response = await api<{ job: Job }>("/loop/run", { method: "POST", body: JSON.stringify({
        async_run: true,
        seed: Number(runSettings.seed),
        benign_count: Number(runSettings.benign_count),
        per_attack_card: Number(runSettings.per_attack_card),
        mutation_candidate_limit: Number(runSettings.mutation_candidate_limit),
        review_source_iteration_id: runSettings.review_source_iteration_id || null,
      }) });
      setJob(response.job); onNotice("Iteration queued. Live status is now tracking.");
    } catch (error) { onNotice(error instanceof Error ? error.message : "Could not start iteration"); }
  }
  async function review(mutationId: string, decision: "accepted" | "rejected") {
    if (!selectedId) return;
    try { await api(`/loop/iterations/${selectedId}/mutations/${mutationId}/review`, { method: "POST", body: JSON.stringify({ decision, reviewer: "web" }) }); await loadDetail(selectedId); }
    catch (error) { onNotice(error instanceof Error ? error.message : "Could not save review"); }
  }
  async function compare() {
    if (iterations.length < 2) { onNotice("Complete at least two iterations before comparing."); return; }
    try { setComparison(await api(`/loop/compare?baseline=${iterations.at(-2)!.iteration_id}&candidate=${iterations.at(-1)!.iteration_id}`)); }
    catch (error) { onNotice(error instanceof Error ? error.message : "Could not compare iterations"); }
  }
  const reviewById = Object.fromEntries(mutationData.reviews.map((item) => [item.mutation_id, item.decision]));
  const stageIndex = Math.max(0, stages.indexOf(job?.stage ?? "queued"));
  return <section className="loop-workspace">
    <article className="panel run-panel"><div><p className="eyebrow accent">CLOSED-LOOP EXECUTION</p><h3>{job && job.status !== "completed" ? `Currently ${prettify(job.stage)}` : "Run a new red-team / blue-team iteration"}</h3><p>Generate attacks, train the detector, analyze weak groups, then propose reviewable mutations.</p><div className="run-controls"><label>Seed<input type="number" value={runSettings.seed} onChange={(event) => setRunSettings({ ...runSettings, seed: event.target.value })}/></label><label>Benign records<input type="number" min="0" value={runSettings.benign_count} onChange={(event) => setRunSettings({ ...runSettings, benign_count: event.target.value })}/></label><label>Scenarios/card<input type="number" min="1" max="10" value={runSettings.per_attack_card} onChange={(event) => setRunSettings({ ...runSettings, per_attack_card: event.target.value })}/></label><label>Review candidates<input type="number" min="1" max="10" value={runSettings.mutation_candidate_limit} onChange={(event) => setRunSettings({ ...runSettings, mutation_candidate_limit: event.target.value })}/></label><label>Use accepted mutations<select value={runSettings.review_source_iteration_id} onChange={(event) => setRunSettings({ ...runSettings, review_source_iteration_id: event.target.value })}><option value="">None</option>{iterations.map((item) => <option value={item.iteration_id} key={item.iteration_id}>{item.iteration_id}</option>)}</select></label></div></div><button className="primary-button" disabled={!!job && ["queued", "running"].includes(job.status)} onClick={() => void startRun()}><Play size={15}/>{job && ["queued", "running"].includes(job.status) ? "Running…" : "Run iteration"}</button></article>
    {job && <article className="panel progress-panel"><div className="panel-title"><h3>Live pipeline status</h3><span>{job.status}</span></div><div className="stage-track">{stages.map((stage, index) => <div className={index <= stageIndex ? "stage done" : "stage"} key={stage}><i>{index < stageIndex || job.stage === "completed" ? <Check size={12}/> : index + 1}</i><small>{prettify(stage)}</small></div>)}</div>{job.error && <p className="error-text">{job.error}</p>}</article>}
    <section className="loop-grid"><article className="panel iteration-browser"><div className="panel-title"><div><h3>Iterations</h3><p>Newest first. Select a completed run to inspect its evidence.</p></div><button className="ghost-button" onClick={() => void compare()}>Compare latest</button></div>{iterations.length ? <><div className="iteration-list">{visibleIterations.map((item) => <button className={item.iteration_id === selectedId ? "iteration selected" : "iteration"} key={item.iteration_id} onClick={() => setSelectedId(item.iteration_id)}><div><span className="iteration-label">{item.iteration_id}</span><h4>{item.counts.transactions ?? 0} simulated transactions</h4><p>Seed {item.seed} · {item.counts.mutation_candidates ?? 0} proposals</p></div><div className="iteration-metrics"><span>F1 <b>{metric(item.evaluation_overall.f1)}</b></span></div></button>)}</div><div className="iteration-pagination"><button className="ghost-button" disabled={iterationPage === 1} onClick={() => setIterationPage(iterationPage - 1)}>Previous</button><span>Page {iterationPage} of {iterationPageCount}</span><button className="ghost-button" disabled={iterationPage === iterationPageCount} onClick={() => setIterationPage(iterationPage + 1)}>Next</button></div></> : <Empty text="No completed iterations yet."/>}</article>
    <article className="panel detail-panel">{detail ? <><div className="panel-title"><div><h3>{detail.iteration_id} evidence</h3><p>Generated data, defense outcomes, and feedback signals.</p></div><span>seed {detail.seed}</span></div><div className="mini-stat-grid"><Stat label="Transactions" value={String(detail.counts.transactions)} detail={`${detail.benign_count} benign records`}/><Stat label="Features" value={String(detail.counts.feature_columns)} detail={`${detail.counts.features} rows scored`}/><Stat label="F1 score" value={metric(detail.evaluation_overall.f1)} detail={`Threshold ${detail.evaluation_overall.threshold ?? "—"}`}/><Stat label="Mutations" value={String(detail.counts.mutation_candidates)} detail={`${detail.counts.accepted_mutations_consumed ?? 0} prior proposals consumed`}/></div><h4 className="section-label">Weakest fraud groups</h4><div className="weak-list">{detail.failure_summary.weak_groups.slice(0, 5).map((group) => <div key={group.group_key}><span>{prettify(group.subtype)}</span><small>{metric(group.avg_fraud_score)} avg score · {group.fraud_count} fraud records · {group.miss_count} misses</small></div>)}</div></> : <Empty text="Select an iteration to load its details."/>}</article></section>
    <IterationTrends iterations={iterations}/>
    {detail && <MutationImpactPanel iterationId={detail.iteration_id}/>} 
    {comparison && <article className="panel comparison"><div className="panel-title"><div><h3>Latest iteration comparison</h3><p>Candidate minus baseline; positive is better except false-positive rate.</p></div></div><div className="delta-grid">{Object.entries(comparison.metric_deltas).map(([name, value]) => <div key={name}><small>{prettify(name)}</small><strong className={value >= 0 ? "positive" : "negative"}>{value >= 0 ? "+" : ""}{(value * 100).toFixed(2)}pp</strong></div>)}</div></article>}
    {detail && <IterationUsage iterationId={detail.iteration_id}/>} {detail && <TransactionExplorer iterationId={detail.iteration_id}/>} {detail && <article className="panel mutation-panel"><div className="panel-title"><div><h3>Human mutation review</h3><p>Inspect the held-out detection gap and exact generator changes before accepting a variant.</p></div><span>{mutationData.candidates.length} candidates</span></div>{mutationData.candidates.length ? <div className="mutation-list">{mutationData.candidates.map((item) => <article className="mutation" key={item.mutation_id}><div className="mutation-body"><span className="chip">{prettify(item.subtype)}</span><h4>{item.proposed_variant_name}</h4><p>{item.rationale}</p>{item.review_evidence && <MutationEvidencePanel evidence={item.review_evidence}/>}<div className="mutation-deltas">{item.parameter_deltas?.map((delta) => <div key={delta.field}><HelpLabel label={prettify(delta.field)} definition={mutationParameterDefinitions[delta.field] ?? "A generator parameter changed for this candidate. The purpose below explains why the red-team simulation adjusts it."}/><span>{formatMutationValue(delta.baseline)} <b>→</b> {formatMutationValue(delta.proposed)}</span><small>{delta.purpose}</small></div>)}</div><small>{item.mutation_strategy.map(prettify).join(" · ")} · {item.provider}{item.gateway_fallback ? " · safe fallback" : ""}</small></div><div className="review-actions">{reviewById[item.mutation_id] ? <span className={`reviewed ${reviewById[item.mutation_id]}`}>{prettify(reviewById[item.mutation_id])}</span> : <><button className="accept" onClick={() => void review(item.mutation_id, "accepted")}><Check size={14}/> Accept</button><button className="reject" onClick={() => void review(item.mutation_id, "rejected")}><X size={14}/> Reject</button></>}</div></article>)}</div> : <Empty text="This iteration produced no mutation proposals."/>}</article>}
  </section>;
}

function MutationEvidencePanel({ evidence }: { evidence: MutationEvidence }) {
  return <section className="mutation-evidence"><div className="evidence-heading"><strong>Why human review is needed</strong><span>{prettify(evidence.evaluation_scope)}</span></div><div className="evidence-metrics"><div><HelpLabel label="Trigger" definition="The observed detector weakness that caused this attack subtype to be selected for a proposed red-team variant."/><b>{prettify(evidence.selection_reason)}</b></div><div><HelpLabel label="Held-out recall" definition="The share of fraud records detected for this subtype when its attack card was excluded from detector training. Lower values indicate weaker generalization."/><b>{metric(evidence.recall)}</b></div><div><HelpLabel label="Misses" definition="Fraud records not flagged by the final detector, shown as misses out of all held-out fraud records for this subtype."/><b>{evidence.miss_count} / {evidence.fraud_count}</b></div><div><HelpLabel label="Avg. fraud score" definition="Average final fraud-risk score assigned to this subtype. Scores closer to the configured threshold are less confidently detected."/><b>{metric(evidence.average_fraud_score)}</b></div></div>{evidence.representative_records.length > 0 && <div className="evidence-examples"><HelpLabel label="Representative weak records" definition="A small sample of missed or lowest-confidence held-out fraud records that illustrates the weakness driving this review."/>{evidence.representative_records.map((record) => <p key={record.transaction_id}><b>{record.transaction_id}</b> · score {metric(record.fraud_score)}{record.reason_codes ? ` · ${record.reason_codes}` : ""}</p>)}</div>}</section>;
}

function HelpLabel({ label, definition }: { label: string; definition: string }) { return <span className="help-label"><small>{label}</small><span className="help-icon" tabIndex={0} aria-label={`${label}: ${definition}`}>?</span><span className="help-tooltip" role="tooltip">{definition}</span></span>; }

function IterationTrends({ iterations }: { iterations: Iteration[] }) {
  const points = iterations.slice(-12).map((iteration) => ({
    id: iteration.iteration_id.replace("iteration_", "#"),
    f1: Number(iteration.evaluation_overall.f1 ?? 0),
    recall: Number(iteration.evaluation_overall.recall ?? 0),
    falsePositiveRate: Number(iteration.evaluation_overall.false_positive_rate ?? 0),
  }));
  const chartWidth = 620; const chartHeight = 244; const left = 42; const right = 18; const top = 18; const bottom = 34;
  const plotWidth = chartWidth - left - right; const plotHeight = chartHeight - top - bottom;
  const x = (index: number) => points.length < 2 ? left + plotWidth / 2 : left + (index * plotWidth) / (points.length - 1);
  const y = (value: number) => top + (1 - Math.max(0, Math.min(1, value))) * plotHeight;
  const path = (key: "f1" | "recall" | "falsePositiveRate") => points.map((point, index) => `${index === 0 ? "M" : "L"}${x(index).toFixed(1)},${y(point[key]).toFixed(1)}`).join(" ");
  const series = [
    { key: "f1" as const, label: "F1", color: "#70e5c8" },
    { key: "recall" as const, label: "Recall", color: "#7cadff" },
    { key: "falsePositiveRate" as const, label: "False-positive rate", color: "#ffbd63" },
  ];
  return <article className="panel trend-panel"><div className="panel-title"><div><h3>Iteration trends</h3><p>Detection quality across the latest {points.length} completed runs.</p></div><span>{points.length} runs</span></div>{points.length < 2 ? <Empty text="Complete one more iteration to compare performance over time."/> : <><div className="trend-legend">{series.map((item) => <span key={item.key}><i style={{ backgroundColor: item.color }}/>{item.label}</span>)}</div><div className="trend-chart-wrap"><svg className="trend-chart" viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label="F1, recall, and false-positive-rate trends by completed iteration"><title>Detection quality by iteration</title>{[0, .25, .5, .75, 1].map((value) => <g key={value}><line x1={left} x2={chartWidth - right} y1={y(value)} y2={y(value)} className="trend-grid"/><text x={left - 8} y={y(value) + 4} textAnchor="end" className="trend-axis">{Math.round(value * 100)}%</text></g>)}{series.map((item) => <path key={item.key} d={path(item.key)} className="trend-line" style={{ stroke: item.color }} />)}{series.flatMap((item) => points.map((point, index) => <circle key={`${item.key}-${point.id}`} cx={x(index)} cy={y(point[item.key])} r="3.5" fill={item.color}><title>{`${point.id}: ${item.label} ${metric(point[item.key])}`}</title></circle>))}{points.map((point, index) => <text key={point.id} x={x(index)} y={chartHeight - 10} textAnchor="middle" className="trend-axis">{point.id}</text>)}</svg></div><div className="trend-summary">{series.map((item) => <div key={item.key}><small>{item.label} latest</small><strong style={{ color: item.color }}>{metric(points.at(-1)?.[item.key])}</strong></div>)}</div></>}</article>;
}

function MutationImpactPanel({ iterationId }: { iterationId: string }) {
  const [impact, setImpact] = useState<MutationImpact | null>(null);
  const [experiment, setExperiment] = useState<ControlledExperiment | null>(null);
  const [experimentBusy, setExperimentBusy] = useState(false);
  const [selectedMutationId, setSelectedMutationId] = useState("");
  const [experimentError, setExperimentError] = useState("");
  const [llmText, setLlmText] = useState(""); const [llmStatus, setLlmStatus] = useState(""); const [llmProvider, setLlmProvider] = useState("");
  useEffect(() => { setImpact(null); setExperiment(null); setSelectedMutationId(""); setExperimentError(""); void api<MutationImpact>(`/loop/iterations/${iterationId}/mutation-impact`).then(setImpact).catch(() => setImpact(null)); }, [iterationId]);
  if (!impact?.outcome || !impact.source_iteration_id) return null;
  const metrics = ["f1", "recall", "precision", "false_positive_rate"];
  const selectedMutation = impact.accepted_mutations.find((item) => item.mutation_id === selectedMutationId) ?? impact.accepted_mutations[0];
  async function runExperiment() { if (!selectedMutation) return; setExperimentBusy(true); setExperimentError(""); setLlmText(""); try { const response = await api<{ experiment: ControlledExperiment }>(`/loop/iterations/${iterationId}/mutation-experiments`, { method: "POST", body: JSON.stringify({ mutation_id: selectedMutation.mutation_id }) }); setExperiment(response.experiment); } catch (error) { setExperimentError(error instanceof Error ? error.message : "Could not run the controlled experiment."); } finally { setExperimentBusy(false); } }
  async function askLlm() { if (!experiment) return; setLlmText(""); setLlmStatus("Connecting to the configured provider…"); setLlmProvider(""); try { const response = await fetch(`${API_URL}/loop/iterations/${iterationId}/mutation-experiments/${experiment.mutation.mutation_id}/explain/stream`); if (!response.ok) throw new Error(`Explanation request failed (${response.status})`); const reader = response.body?.getReader(); if (!reader) throw new Error("Streaming is unavailable."); const decoder = new TextDecoder(); let buffer = ""; while (true) { const next = await reader.read(); if (next.done) break; buffer += decoder.decode(next.value, { stream: true }); const events = buffer.split("\n\n"); buffer = events.pop() ?? ""; for (const event of events) { const kind = event.match(/event: (.+)/)?.[1]; const data = event.match(/data: (.+)/)?.[1]; if (!kind || !data) continue; const payload = JSON.parse(data); if (kind === "status") setLlmStatus(payload.message); if (kind === "meta") { setLlmProvider(payload.provider); setLlmStatus("Writing a concise interpretation…"); } if (kind === "token") setLlmText((current) => current + payload.text); if (kind === "done") setLlmStatus(""); } } } catch (error) { setLlmStatus(error instanceof Error ? error.message : "Could not obtain an LLM interpretation."); } }
  return <article className="panel mutation-impact"><div className="panel-title"><div><h3>Accepted mutation: before vs. after</h3><p>{impact.source_iteration_id} → {iterationId} · {impact.outcome.overlays_applied} runtime overlays applied</p></div><span>{impact.outcome.mutations_consumed} consumed</span></div><div className="impact-metrics">{metrics.map((name) => { const delta = impact.outcome!.metric_deltas[name] ?? 0; const favorable = name === "false_positive_rate" ? delta <= 0 : delta >= 0; return <div key={name}><small>{prettify(name)}</small><strong>{metric(impact.outcome!.source_metrics[name])} <b>→</b> {metric(impact.outcome!.candidate_metrics[name])}</strong><span className={favorable ? "positive" : "negative"}>{delta >= 0 ? "+" : ""}{(delta * 100).toFixed(2)}pp</span></div>; })}</div><div className="impact-mutations"><HelpLabel label="Accepted variants included" definition="These reviewed mutation proposals were selected from the source iteration and applied as runtime attack-card overlays in the candidate iteration."/>{impact.accepted_mutations.slice(0, 4).map((item) => <span className="chip" key={item.mutation_id}>{prettify(item.subtype)} · {item.proposed_variant_name}</span>)}{impact.accepted_mutations.length > 4 && <span className="chip">+{impact.accepted_mutations.length - 4} more</span>}</div><p className="impact-disclosure">{impact.disclosure}</p><div className="experiment-actions"><label className="experiment-selector">Mutation to evaluate<select value={selectedMutation?.mutation_id ?? ""} onChange={(event) => { setSelectedMutationId(event.target.value); setExperiment(null); setLlmText(""); setExperimentError(""); }}>{impact.accepted_mutations.map((item) => <option key={item.mutation_id} value={item.mutation_id}>{prettify(item.subtype)} · {item.proposed_variant_name}</option>)}</select></label><button className="primary-button" disabled={experimentBusy || !selectedMutation} onClick={() => void runExperiment()}>{experimentBusy ? "Running controlled experiment…" : "Run controlled experiment"}</button><small>Matched seed, volume, benign records, and frozen source detector.</small></div>{experimentError && <p className="error-text">{experimentError}</p>}{experiment && <section className="controlled-result"><h4>Controlled experiment: {experiment.mutation.proposed_variant_name}</h4><p className="deterministic-explanation">{experiment.deterministic_explanation}</p><div className="impact-metrics">{["f1", "recall", "precision", "false_positive_rate"].map((name) => <div key={name}><small>{prettify(name)}</small><strong>{metric(experiment.baseline.metrics[name])} <b>→</b> {metric(experiment.mutated.metrics[name])}</strong><span>{(experiment.metric_deltas[name] * 100).toFixed(2)}pp</span></div>)}</div><div className="experiment-actions"><button className="ghost-button" onClick={() => void askLlm()}>Ask LLM</button><small>Only aggregate metrics and declared mutation settings are sent.</small></div>{llmStatus && <p className="llm-status">{llmStatus}</p>}{llmText && <p className="llm-explanation"><b>LLM interpretation{llmProvider ? ` · ${llmProvider}` : ""}</b>{llmText}</p>}<p className="impact-disclosure">{experiment.disclosure}</p></section>}</article>;
}

type PortfolioManifest = { dataset_id: string; dataset_name: string; row_counts: { historical: number; upcoming: number }; data_quality: Record<string, { missing_optional_values?: Record<string, number>; unrecognized_columns_ignored?: string[] }>; warnings: string[] };
type PortfolioScore = { dataset_id: string; mode: string; model_source: string; upcoming_count: number; flagged_count: number; results: Record<string, string | number>[]; disclosure: string; genai_data_route?: { destination?: string; provider?: string; cloud_acknowledgement_required?: boolean } };

function Portfolio({ iterations, onNotice }: { iterations: Iteration[]; onNotice: (message: string) => void }) {
  const [historical, setHistorical] = useState(""); const [upcoming, setUpcoming] = useState("");
  const [historicalName, setHistoricalName] = useState(""); const [upcomingName, setUpcomingName] = useState("");
  const [dataset, setDataset] = useState<PortfolioManifest | null>(null); const [result, setResult] = useState<PortfolioScore | null>(null);
  const [modelIterationId, setModelIterationId] = useState(""); const [enableGenAI, setEnableGenAI] = useState(false); const [cloudAcknowledged, setCloudAcknowledged] = useState(false); const [busy, setBusy] = useState(false);
  async function downloadTemplates() { try { const template = await api<{ historical_csv: string; upcoming_csv: string }>("/portfolio/template"); downloadCsv("historical_transactions_template.csv", template.historical_csv); downloadCsv("upcoming_transactions_template.csv", template.upcoming_csv); onNotice("CSV templates downloaded. Populate them with pseudonymized demo records, then select both files here."); } catch (error) { onNotice(error instanceof Error ? error.message : "Could not load templates"); } }
  async function readFile(file: File, target: "historical" | "upcoming") { const content = await file.text(); if (target === "historical") { setHistorical(content); setHistoricalName(file.name); } else { setUpcoming(content); setUpcomingName(file.name); } }
  async function create() { if (!historical || !upcoming) { onNotice("Provide both historical and upcoming CSV files first."); return; } setBusy(true); try { const response = await api<{ dataset: PortfolioManifest }>("/portfolio/datasets", { method: "POST", body: JSON.stringify({ dataset_name: "local_judge_demo", historical_csv: historical, upcoming_csv: upcoming }) }); setDataset(response.dataset); setResult(null); onNotice("Local demo dataset validated and prepared. No GenAI review has been run."); } catch (error) { onNotice(error instanceof Error ? error.message : "Portfolio validation failed"); } finally { setBusy(false); } }
  async function score() { if (!dataset) return; setBusy(true); try { const response = await api<PortfolioScore>(`/portfolio/datasets/${dataset.dataset_id}/score`, { method: "POST", body: JSON.stringify({ model_iteration_id: modelIterationId || null, enable_genai_review: enableGenAI, cloud_data_acknowledged: cloudAcknowledged }) }); setResult(response); onNotice(`Advisory scoring completed: ${response.flagged_count} of ${response.upcoming_count} upcoming records flagged.`); } catch (error) { onNotice(error instanceof Error ? error.message : "Could not score portfolio"); } finally { setBusy(false); } }
  async function remove() { if (!dataset) return; try { await api(`/portfolio/datasets/${dataset.dataset_id}`, { method: "DELETE" }); setDataset(null); setResult(null); onNotice("Local demo dataset deleted."); } catch (error) { onNotice(error instanceof Error ? error.message : "Could not delete dataset"); } }
  return <section className="portfolio-workspace"><article className="panel portfolio-notice"><p className="eyebrow accent">LOCAL DEMO DATA ONLY</p><h3>Portfolio onboarding and advisory scoring</h3><p>Use pseudonymized, authorized demo data only. Never upload PAN, account numbers, CVV, direct PII, or production records.</p></article><article className="panel portfolio-upload"><div className="panel-title"><div><h3>1. Prepare input files</h3><p>Historical activity establishes behavior; upcoming transactions are scored against that history.</p></div><button className="ghost-button" onClick={() => void downloadTemplates()}>Download CSV templates</button></div><div className="upload-grid"><label>Historical transactions<input type="file" accept=".csv,text/csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void readFile(file, "historical"); }}/><small>{historicalName || "No file selected"}</small></label><label>Upcoming transactions<input type="file" accept=".csv,text/csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void readFile(file, "upcoming"); }}/><small>{upcomingName || "No file selected"}</small></label></div><div className="upload-actions"><button className="primary-button" disabled={busy} onClick={() => void create()}>{busy ? "Validating…" : "Validate & prepare dataset"}</button><small>Download the templates, add pseudonymized records, then select both completed CSV files.</small></div></article>{dataset && <><article className="panel portfolio-ready"><div className="panel-title"><div><h3>2. Dataset readiness</h3><p>{dataset.dataset_name} · {dataset.dataset_id}</p></div><button className="reject" onClick={() => void remove()}>Delete local dataset</button></div><div className="mini-stat-grid"><Stat label="Historical" value={String(dataset.row_counts.historical)} detail="Behavioral baseline records"/><Stat label="Upcoming" value={String(dataset.row_counts.upcoming)} detail="Advisory scoring records"/><Stat label="Storage" value="Local" detail="Demo-only run directory"/><Stat label="GenAI default" value="Off" detail="No uploaded data routed yet"/></div>{dataset.warnings.map((warning) => <p className="portfolio-warning" key={warning}>{warning}</p>)}</article><article className="panel portfolio-score"><div className="panel-title"><div><h3>3. Score upcoming transactions</h3><p>Select a freshly trained closed-loop detector. Results are advisory until portfolio-specific backtesting is performed.</p></div></div><div className="score-controls"><label>Detector iteration<select value={modelIterationId} onChange={(event) => setModelIterationId(event.target.value)}><option value="">Newest available model</option>{iterations.map((iteration) => <option value={iteration.iteration_id} key={iteration.iteration_id}>{iteration.iteration_id}</option>)}</select></label><label className="check-label"><input type="checkbox" checked={enableGenAI} onChange={(event) => setEnableGenAI(event.target.checked)}/> Enable selective GenAI review</label>{enableGenAI && <label className="check-label"><input type="checkbox" checked={cloudAcknowledged} onChange={(event) => setCloudAcknowledged(event.target.checked)}/> I understand a cloud-configured reviewer may receive selected record context</label>}<button className="primary-button" disabled={busy} onClick={() => void score()}>{busy ? "Scoring…" : "Run advisory scoring"}</button></div></article></>}{result && <article className="panel portfolio-results"><div className="panel-title"><div><h3>Advisory scoring results</h3><p>{result.disclosure}</p></div><span>{result.flagged_count} flagged</span></div>{result.genai_data_route?.destination && <p className="credential-note">GenAI route: {result.genai_data_route.provider} · {prettify(result.genai_data_route.destination)}</p>}<div className="table-wrap"><table><thead><tr><th>Transaction</th><th>ML score</th><th>Final score</th><th>Decision</th><th>Reason codes</th></tr></thead><tbody>{result.results.map((row) => <tr key={String(row.transaction_id)}><td>{String(row.transaction_id)}</td><td>{metric(Number(row.ml_fraud_score))}</td><td>{metric(Number(row.fraud_score))}</td><td><span className={Number(row.prediction) ? "reviewed accepted" : "reviewed"}>{Number(row.prediction) ? "Flagged" : "Cleared"}</span></td><td>{String(row.reason_codes || "—")}</td></tr>)}</tbody></table></div></article>}</section>;
}

function IterationUsage({ iterationId }: { iterationId: string }) {
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  useEffect(() => { void api<UsageSummary>(`/loop/iterations/${iterationId}/genai-usage`).then(setUsage).catch(() => setUsage(null)); }, [iterationId]);
  if (!usage) return null;
  return <article className="panel usage-panel"><div className="panel-title"><div><h3>GenAI iteration economics</h3><p>Measured gateway activity for {iterationId}; cloud figures are what-if estimates, not invoices.</p></div><span>{usage.call_count} calls</span></div>{usage.call_count === 0 ? <Empty text="No attributed GenAI calls for this historical iteration. Run a new iteration after configuring LM Studio to populate this view."/> : <><div className="mini-stat-grid usage-stats"><Stat label="Input tokens" value={String(usage.input_tokens_estimated)} detail="Estimated"/><Stat label="Output tokens" value={String(usage.output_tokens_estimated)} detail="Estimated"/><Stat label="Gateway latency" value={`${usage.latency_ms_total} ms`} detail="Total measured time"/><Stat label="Local estimated cost" value="USD 0" detail="Mac-hosted inference"/></div><h4 className="section-label">Equivalent provider cost for this iteration</h4><div className="cost-grid iteration-cost-grid">{usage.cost_estimates.map((item) => <div key={item.model_key}><small>{prettify(item.provider)}</small><strong>{item.currency} {item.estimated_total_cost.toFixed(6)}</strong><span>{item.model || item.model_key}</span></div>)}</div><h4 className="section-label">Gateway call ledger</h4><div className="table-wrap"><table><thead><tr><th>Time</th><th>Task</th><th>Provider</th><th>Tokens</th><th>Latency</th><th>Result</th></tr></thead><tbody>{usage.calls.map((call, index) => <tr key={`${call.timestamp}-${index}`}><td>{new Date(call.timestamp).toLocaleTimeString()}</td><td>{prettify(call.task)}</td><td><span className="chip">{call.provider}</span></td><td>{call.input_tokens_estimated} in<small>{call.output_tokens_estimated} out</small></td><td>{call.latency_ms ?? "—"} ms</td><td><span className={call.fallback ? "severity medium" : "severity low"}>{call.fallback ? `Fallback: ${call.fallback.to_provider}` : "Direct"}</span></td></tr>)}</tbody></table></div></>}</article>;
}

function TransactionExplorer({ iterationId }: { iterationId: string }) {
  const [data, setData] = useState<TransactionPage | null>(null);
  const [loading, setLoading] = useState(false);
  const requestVersion = useRef(0);
  const [page, setPage] = useState(1);
  const [label, setLabel] = useState("");
  const [bucket, setBucket] = useState("");
  const [flagged, setFlagged] = useState("");
  const [llmReviewed, setLlmReviewed] = useState("");
  const [decisionEngine, setDecisionEngine] = useState("");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("event_time");
  const [sortDirection, setSortDirection] = useState("desc");
  const [showColumns, setShowColumns] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState<string[]>(["transaction_id", "context", "label", "ml_fraud_score", "llm_reviewed", "fraud_score", "prediction"]);
  const [selected, setSelected] = useState<TransactionDetail | null>(null);
  useEffect(() => { setPage(1); setLabel(""); setBucket(""); setFlagged(""); setLlmReviewed(""); setDecisionEngine(""); setSearch(""); }, [iterationId]);
  useEffect(() => { void load(); }, [iterationId, page, label, bucket, flagged, llmReviewed, decisionEngine, search, sortBy, sortDirection]);
  async function load() {
    const currentRequest = ++requestVersion.current;
    const params = new URLSearchParams({ page: String(page), page_size: "12", sort_by: sortBy, sort_direction: sortDirection });
    if (label) params.set("label", label); if (bucket) params.set("bucket", bucket); if (flagged) params.set("flagged", flagged); if (llmReviewed) params.set("llm_reviewed", llmReviewed); if (decisionEngine) params.set("decision_engine", decisionEngine); if (search.trim()) params.set("search", search.trim());
    setLoading(true);
    try {
      const next = await api<TransactionPage>(`/loop/iterations/${iterationId}/transactions?${params}`);
      if (currentRequest === requestVersion.current) setData(next);
    } catch {
      if (currentRequest === requestVersion.current) setData(null);
    } finally {
      if (currentRequest === requestVersion.current) setLoading(false);
    }
  }
  async function openDetail(transactionId: string) {
    try { setSelected(await api<TransactionDetail>(`/loop/iterations/${iterationId}/transactions/${transactionId}`)); } catch { setSelected(null); }
  }
  function changeSort(column: string) { if (sortBy === column) setSortDirection(sortDirection === "asc" ? "desc" : "asc"); else { setSortBy(column); setSortDirection("asc"); } setPage(1); }
  function toggleColumn(column: string) { setVisibleColumns(visibleColumns.includes(column) ? visibleColumns.filter((item) => item !== column) : [...visibleColumns, column]); }
  const columns: { key: string; label: string; sortKey: string; render: (item: TransactionRecord) => React.ReactNode }[] = [
    { key: "transaction_id", label: "Transaction", sortKey: "transaction_id", render: (item) => <><strong>{item.transaction_id}</strong><small>{new Date(item.event_time).toLocaleString()}</small></> },
    { key: "context", label: "Context", sortKey: "amount", render: (item) => <>{item.currency} {item.amount.toFixed(2)}<small>{item.channel} · {item.rail} · {item.merchant_category}</small></> },
    { key: "label", label: "Label", sortKey: "label", render: (item) => <span className={item.label ? "severity high" : "severity low"}>{item.label ? prettify(item.attack_subtype || "Fraud") : "Legitimate"}</span> },
    { key: "ml_fraud_score", label: "ML score", sortKey: "ml_fraud_score", render: (item) => <strong>{metric(item.ml_fraud_score)}</strong> },
    { key: "llm_reviewed", label: "LLM review", sortKey: "llm_reviewed", render: (item) => <>{item.llm_reviewed ? <span className="reviewed accepted">Reviewed</span> : <span className="reviewed">Not reviewed</span>}<small>{item.llm_provider || "—"}</small></> },
    { key: "llm_semantic_risk_score", label: "Semantic risk", sortKey: "llm_semantic_risk_score", render: (item) => item.llm_semantic_risk_score === null ? "—" : metric(item.llm_semantic_risk_score) },
    { key: "fraud_score", label: "Final score", sortKey: "fraud_score", render: (item) => <><strong>{metric(item.fraud_score)}</strong><small>{item.decision_engine}</small></> },
    { key: "prediction", label: "Final decision", sortKey: "prediction", render: (item) => <span className={item.prediction ? "reviewed accepted" : "reviewed"}>{item.prediction ? "Flagged" : "Cleared"}</span> },
  ];
  const shownColumns = columns.filter((column) => visibleColumns.includes(column.key));
  return <><article className="panel explorer"><div className="panel-title"><div><h3>Synthetic payment explorer</h3><p>Sort, filter, and select a row for full hybrid-decision evidence.</p></div><div className="explorer-actions"><span>{loading ? "Filtering…" : `${data?.total ?? 0} matching records`}</span><button className="ghost-button" onClick={() => setShowColumns(!showColumns)}><Columns3 size={14}/> Columns</button>{showColumns && <div className="column-picker">{columns.map((column) => <label key={column.key}><input type="checkbox" checked={visibleColumns.includes(column.key)} onChange={() => toggleColumn(column.key)}/>{column.label}</label>)}</div>}</div></div><div className="explorer-filters"><label className="explorer-search"><span><Search size={13}/> Search records</span><input value={search} placeholder="ID, channel, subtype…" onChange={(event) => { setSearch(event.target.value); setPage(1); }}/></label><label>Label<select value={label} onChange={(event) => { setLabel(event.target.value); setPage(1); }}><option value="">All labels</option><option value="0">Legitimate</option><option value="1">Fraud</option></select></label><label>Family<select value={bucket} onChange={(event) => { setBucket(event.target.value); setPage(1); }}><option value="">All families</option>{data?.filters.buckets.map((item) => <option value={item} key={item}>{prettify(item)}</option>)}</select></label><label>Final decision<select value={flagged} onChange={(event) => { setFlagged(event.target.value); setPage(1); }}><option value="">All outcomes</option><option value="1">Flagged</option><option value="0">Cleared</option></select></label><label>LLM review<select value={llmReviewed} onChange={(event) => { setLlmReviewed(event.target.value); setPage(1); }}><option value="">All rows</option><option value="1">Reviewed</option><option value="0">Not reviewed</option></select></label><label>Decision engine<select value={decisionEngine} onChange={(event) => { setDecisionEngine(event.target.value); setPage(1); }}><option value="">All engines</option>{data?.filters.decision_engines.map((item) => <option value={item} key={item}>{prettify(item)}</option>)}</select></label></div><div className="table-wrap"><table><thead><tr>{shownColumns.map((column) => <th key={column.key}><button className="sort-header" onClick={() => changeSort(column.sortKey)}>{column.label}<span>{sortBy === column.sortKey ? (sortDirection === "asc" ? "▲" : "▼") : "↕"}</span></button></th>)}</tr></thead><tbody>{data?.items.map((item) => <tr className="clickable-row" key={item.transaction_id} onClick={() => void openDetail(item.transaction_id)}>{shownColumns.map((column) => <td key={column.key}>{column.render(item)}</td>)}</tr>)}</tbody></table></div><div className="pagination"><button className="ghost-button" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page} of {Math.max(1, Math.ceil((data?.total ?? 0) / 12))}</span><button className="ghost-button" disabled={!data || page * 12 >= data.total} onClick={() => setPage(page + 1)}>Next</button></div></article>{selected && <TransactionModal detail={selected} onClose={() => setSelected(null)}/>}</>;
}

function TransactionModal({ detail, onClose }: { detail: TransactionDetail; onClose: () => void }) {
  const sections: [string, Record<string, string> | null][] = [["Transaction", detail.transaction], ["Customer context", detail.entities.customer], ["Merchant context", detail.entities.merchant], ["Device context", detail.entities.device], ["Attack scenario", detail.attack_instance]];
  const decision = detail.decision_provenance;
  const primaryDecision = { primary_engine: decision.primary_engine, ml_fraud_score: decision.ml_fraud_score, ml_prediction: decision.ml_prediction, ml_reason_codes: decision.ml_reason_codes };
  const llmDecision = { llm_reviewed: decision.llm_reviewed, llm_provider: decision.llm_provider, llm_semantic_risk_score: decision.llm_semantic_risk_score, llm_novelty_score: decision.llm_novelty_score, llm_recommendation: decision.llm_recommendation, llm_rationale: decision.llm_rationale, llm_risk_indicators: decision.llm_risk_indicators, llm_fallback: decision.llm_fallback };
  const finalDecision = { final_engine: decision.final_engine, final_fraud_score: decision.final_fraud_score, final_prediction: decision.final_prediction };
  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="record-modal" role="dialog" aria-modal="true" aria-label="Transaction detail" onMouseDown={(event) => event.stopPropagation()}><div className="panel-title"><div><p className="eyebrow accent">TRANSACTION EVIDENCE</p><h3>{detail.transaction.transaction_id}</h3><p>Complete synthetic record, generation lineage, and hybrid decision evidence.</p></div><button className="modal-close" onClick={onClose}><X size={18}/></button></div><section className="detection-summary"><div><small>Final fraud score</small><strong>{metric(Number(decision.final_fraud_score ?? detail.detection.fraud_score ?? 0))}</strong></div><div><small>Final outcome</small><strong>{String(decision.final_prediction ?? detail.detection.prediction) === "1" ? "Flagged" : "Cleared"}</strong></div><div><small>True label</small><strong>{detail.detection.label === "1" ? "Fraud" : "Legitimate"}</strong></div></section><div className="provenance-sections"><EvidenceSection title="Generation provenance" record={detail.generation_provenance}/><EvidenceSection title="Primary ML decision" record={primaryDecision}/><EvidenceSection title="Selective LLM review" record={llmDecision}/><EvidenceSection title="Final hybrid decision" record={finalDecision}/></div><div className="record-sections">{sections.filter(([, record]) => record).map(([title, record]) => <EvidenceSection key={title} title={title} record={record!}/>)}</div></section></div>;
}

function EvidenceSection({ title, record }: { title: string; record: Record<string, unknown> }) {
  return <section><h4>{title}</h4><dl>{Object.entries(record).map(([key, value]) => <div key={key}><dt>{prettify(key)}</dt><dd>{formatEvidence(value)}</dd></div>)}</dl></section>;
}

function formatEvidence(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join("; ") : "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatMutationValue(value: MutationDelta["baseline"]): string {
  return Array.isArray(value) ? `[${value.join(", ")}]` : String(value);
}

function downloadCsv(filename: string, content: string) {
  const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
}

function Gateway({ providers, onNotice }: { providers: Record<string, Provider>; onNotice: (message: string) => void }) {
  const [selected, setSelected] = useState("local_rules");
  const [values, setValues] = useState<Record<string, string>>({});
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ provider: string; latency_ms: number; usage_estimate: { input_tokens: number; output_tokens: number }; fallback?: { from_provider: string; to_provider: string; reason: string } | null } | null>(null);
  const [costs, setCosts] = useState<{ estimates: { model_key: string; provider: string; estimated_total_cost: number; currency: string }[] } | null>(null);
  const provider = providers[selected];

  function selectProvider(providerId: string) {
    setSelected(providerId);
    setValues(providerId === "local_lmstudio" ? {
      base_url: "http://127.0.0.1:1234/v1",
      timeout_seconds: "120",
      temperature: "0.7",
      max_tokens: "1200",
    } : {});
  }

  async function save(silent = false) {
    if (!provider) return;
    const selectedProvider = { type: provider.type, ...values };
    const taskRoutes = Object.fromEntries([
      "attack_mutation", "attack_ideation", "scenario_narrative", "alert_explanation", "evaluation_summary",
    ].map((task) => [task, selected]));
    const config = {
      default_provider: selected,
      fallback_provider: "local_rules",
      task_routes: taskRoutes,
      providers: {
        local_rules: { type: "local_rules" },
        ...(selected === "local_rules" ? {} : { [selected]: selectedProvider }),
      },
      budget: { max_calls_per_run: 25, max_tokens_per_call: 1200, dry_run: false },
    };
    try {
      await api("/genai/config/session", { method: "POST", body: JSON.stringify({ config }) });
      if (!silent) onNotice("Provider configuration saved for this backend session.");
      return true;
    } catch (error) { onNotice(error instanceof Error ? error.message : "Could not save configuration"); return false; }
  }

  async function testConnection() {
    if (!(await save(true))) return;
    setTesting(true); setTestResult(null); setCosts(null);
    try {
      const result = await api<{ provider: string; latency_ms: number; usage_estimate: { input_tokens: number; output_tokens: number }; fallback?: { from_provider: string; to_provider: string; reason: string } | null }>("/genai/test-connection", { method: "POST", body: JSON.stringify({ task: "attack_mutation" }) });
      setTestResult(result);
      setCosts(await api("/genai/cost/estimate", { method: "POST", body: JSON.stringify(result.usage_estimate) }));
      onNotice(result.fallback ? "Gateway test completed using the configured fallback." : `Gateway test succeeded via ${result.provider}.`);
    } catch (error) { onNotice(error instanceof Error ? error.message : "Gateway test failed"); }
    finally { setTesting(false); }
  }

  return <section className="gateway-layout"><article className="panel provider-list"><div className="panel-title"><div><h3>Model provider</h3><p>Choose the operating context for GenAI tasks.</p></div></div>{Object.entries(providers).map(([key, item]) => <button key={key} className={selected === key ? "provider active" : "provider"} onClick={() => { selectProvider(key); setTestResult(null); setCosts(null); }}><Bot size={18}/><span><strong>{item.label}</strong><small>{item.type}</small></span></button>)}</article><article className="panel config-panel"><div className="panel-title"><div><h3>{provider?.label ?? "Loading providers…"}</h3><p>Configuration is held only in backend memory for this demo. Secret values are never returned to the browser.</p></div></div>{provider && <><div className="form-grid">{provider.fields.map((field) => <label key={field}>{prettify(field)}<input value={values[field] ?? ""} placeholder={field === "base_url" ? "http://127.0.0.1:1234/v1" : `Enter ${prettify(field).toLowerCase()}`} onChange={(event) => setValues({ ...values, [field]: event.target.value })}/></label>)}{provider.secret_fields.map((field) => <label key={field}>{prettify(field)}<input type="password" value={values[field] ?? ""} placeholder={`Enter ${prettify(field).toLowerCase()}`} onChange={(event) => setValues({ ...values, [field]: event.target.value })}/></label>)}</div>{provider.credential_note && <p className="credential-note">{provider.credential_note}</p>}<div className="gateway-actions"><button className="ghost-button" onClick={() => void save()}>Save configuration</button><button className="primary-button" onClick={() => void testConnection()} disabled={testing}>{testing ? "Testing provider…" : "Save & test connection"}</button></div>{testResult && <section className="gateway-result"><div className="panel-title"><div><h3>{testResult.fallback ? "Fallback response" : "Provider response verified"}</h3><p>{testResult.fallback ? `${testResult.fallback.from_provider} failed; ${testResult.fallback.to_provider} answered instead.` : `${testResult.provider} completed the defensive test request.`}</p></div><span>{testResult.latency_ms.toLocaleString()} ms</span></div><div className="mini-stat-grid"><Stat label="Responding provider" value={testResult.provider} detail={testResult.fallback ? "Fallback used" : "Configured provider used"}/><Stat label="Input estimate" value={String(testResult.usage_estimate.input_tokens)} detail="Approximate tokens"/><Stat label="Output estimate" value={String(testResult.usage_estimate.output_tokens)} detail="Approximate tokens"/><Stat label="Latency" value={`${testResult.latency_ms} ms`} detail="End-to-end gateway time"/></div></section>}{costs && <section className="cost-panel"><h4 className="section-label">Approximate equivalent cloud cost</h4><p>Estimated from this test request’s token volume; not a provider invoice.</p><div className="cost-grid">{costs.estimates.map((item) => <div key={item.model_key}><small>{prettify(item.provider)}</small><strong>{item.currency} {item.estimated_total_cost.toFixed(6)}</strong><span>{item.model_key}</span></div>)}</div></section>}</>}</article></section>;
}
function Stat({ label, value, detail }: { label: string; value: string; detail: string }) { return <article className="stat"><p>{label}</p><strong>{value}</strong><small>{detail}</small></article>; }
function Empty({ text }: { text: string }) { return <div className="empty">{text}</div>; }
