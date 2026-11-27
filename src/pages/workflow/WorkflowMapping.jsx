import { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight, ArrowRight, RefreshCw, AlertTriangle, CheckCircle2, HelpCircle } from 'lucide-react';
import {
  analyzeProjectMapping,
  autoRegisterImages,
  getFindings,
  getPanels,
  getProjectImageObjectUrl,
  getProjectMapping,
  getRegistrationOverview,
  registerImages,
} from '../../api';
import { formatGridCoordinate, formatPolygonPoints, getPanelVisualStyle } from '../../utils/panelDetection';

function PanelOverlay({ src, panels, imageSize, selectedPanel, onSelect, findingsByPanel }) {
  const width = imageSize?.width || 1000;
  const height = imageSize?.height || 750;
  return (
    <div style={{ position: 'relative', width: '100%', height: 260, background: '#000', borderRadius: 7, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ position: 'relative', aspectRatio: `${width} / ${height}`, maxWidth: '100%', maxHeight: '100%' }}>
        <img src={src} alt="Localized solar panels" style={{ width: '100%', height: '100%', display: 'block' }} />
        <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
          {(panels || []).map(panel => {
            const { x1, y1, x2, y2 } = panel.bbox;
            const panelFindings = findingsByPanel[panel.panel_id] || findingsByPanel[panel.site_panel_id] || [];
            const visual = getPanelVisualStyle(panel, {
              isSelected: selectedPanel === panel.panel_id,
              findingsForPanel: panelFindings,
            });
            const polyPoints = formatPolygonPoints(panel.geometry);
            const label = panel.row_label && panel.column_label ? `${panel.row_label}${panel.column_label}` : panel.panel_id;
            return (
              <g key={panel.panel_id} onClick={() => onSelect(panel.panel_id)} style={{ pointerEvents: 'all', cursor: 'pointer' }}>
                {polyPoints ? (
                  <polygon points={polyPoints} fill={visual.fill} stroke={visual.stroke} strokeWidth={Math.max(2, width / 750)} />
                ) : (
                  <rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill={visual.fill} stroke={visual.stroke} strokeWidth={Math.max(2, width / 750)} />
                )}
                <text
                  x={(x1 + x2) / 2}
                  y={(y1 + y2) / 2}
                  fill="#fff"
                  stroke="#111827"
                  strokeWidth={Math.max(2, width / 600)}
                  paintOrder="stroke"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={Math.max(12, width / 55)}
                  fontWeight="700"
                >
                  {label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

export default function WorkflowMapping({ project, onNext }) {
  const [thermalIdx, setThermalIdx] = useState(0);
  const [rgbResults, setRgbResults] = useState([]);
  const [rgbIdx, setRgbIdx] = useState(0);
  const [findings, setFindings] = useState([]);
  const [mappingData, setMappingData] = useState(null);
  const [regOverview, setRegOverview] = useState(null);
  const [selectedPanel, setSelectedPanel] = useState(null);
  const [registration, setRegistration] = useState(null);
  const [registering, setRegistering] = useState(false);
  const [analyzingMap, setAnalyzingMap] = useState(false);
  const [panelsLoading, setPanelsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('all');
  const [thermalUrl, setThermalUrl] = useState('');
  const [rgbUrl, setRgbUrl] = useState('');
  const [actionError, setActionError] = useState('');

  const loadMappingState = useCallback(async () => {
    if (!project._id) return;
    setPanelsLoading(true);
    setActionError('');
    try {
      const [panelsRes, findingsRes, mappingRes, regRes] = await Promise.allSettled([
        getPanels(project._id),
        getFindings(project._id, project.jobId),
        getProjectMapping(project._id, project.jobId),
        getRegistrationOverview(project._id),
      ]);
      if (panelsRes.status === 'fulfilled') setRgbResults(panelsRes.value || []);
      if (findingsRes.status === 'fulfilled') setFindings(findingsRes.value || []);
      if (mappingRes.status === 'fulfilled') {
        setMappingData(mappingRes.value);
        if (mappingRes.value?.panelResults?.length) setRgbResults(mappingRes.value.panelResults);
      }
      if (regRes.status === 'fulfilled') setRegOverview(regRes.value);
    } finally {
      setPanelsLoading(false);
    }
  }, [project._id, project.jobId]);

  useEffect(() => {
    loadMappingState();
  }, [loadMappingState]);

  useEffect(() => {
    setRegistration(null);
    setSelectedPanel(null);
  }, [rgbIdx, thermalIdx]);

  useEffect(() => {
    const image = project.thermalImages?.[thermalIdx];
    let disposed = false;
    let objectUrl;
    setThermalUrl('');
    if (project._id && image?.imageId) {
      getProjectImageObjectUrl(project._id, image.imageId).then(url => {
        if (disposed) URL.revokeObjectURL(url);
        else { objectUrl = url; setThermalUrl(url); }
      }).catch(() => setThermalUrl(''));
    }
    return () => { disposed = true; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [project._id, project.thermalImages, thermalIdx]);

  useEffect(() => {
    const image = rgbResults[rgbIdx];
    let disposed = false;
    let objectUrl;
    setRgbUrl('');
    if (project._id && image?.imageId) {
      getProjectImageObjectUrl(project._id, image.imageId).then(url => {
        if (disposed) URL.revokeObjectURL(url);
        else { objectUrl = url; setRgbUrl(url); }
      }).catch(() => setRgbUrl(''));
    }
    return () => { disposed = true; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [project._id, rgbResults, rgbIdx]);

  const thermalImages = project.thermalImages || [];
  const rgbImages = project.rgbImages || [];
  const hasThermal = thermalImages.length > 0;
  const cur = rgbResults[rgbIdx];
  const hasRgb = cur?.status === 'COMPLETED';
  const totalPanels = rgbResults.reduce((s, r) => s + (r.panels?.length || 0), 0);

  const findingsByPanel = findings.reduce((acc, row) => {
    const key = row.panelId || row.sitePanelId;
    if (key) {
      if (!acc[key]) acc[key] = [];
      acc[key].push(row);
    }
    return acc;
  }, {});

  const selectedPanelRecord = (cur?.panels || []).find(p => p.panel_id === selectedPanel) || null;
  const unassignedFindings = findings.filter(r => r.matchStatus === 'UNASSIGNED' || r.matchStatus === 'UNREGISTERED' || !r.panelId);
  const uncertainFindings = findings.filter(r => r.matchStatus === 'REVIEW_REQUIRED' || r.reviewRequired);
  const aggregatedPanels = mappingData?.panelAggregation?.panels || [];
  const aggSummary = mappingData?.panelAggregation?.summary;
  const dedup = mappingData?.deduplication;
  const quality = mappingData?.quality;

  const displayedFindings = selectedPanel
    ? findings.filter(row => row.panelId === selectedPanel || (selectedPanelRecord?.site_panel_id && row.sitePanelId === selectedPanelRecord.site_panel_id))
    : activeTab === 'unassigned'
      ? unassignedFindings
      : activeTab === 'uncertain'
        ? uncertainFindings
        : findings;

  const currentPairRegistration = registration || (regOverview?.registrations || []).find(
    r => r.referenceImageId === cur?.imageId && r.movingImageId === thermalImages[thermalIdx]?.imageId
  );

  const registerCurrentPair = async () => {
    const rgbImage = rgbImages.find(image => image.imageId === cur?.imageId);
    const thermalImage = thermalImages[thermalIdx];
    if (!rgbImage || !thermalImage) return;
    setRegistering(true);
    setActionError('');
    try {
      const result = await registerImages(project._id, rgbImage.imageId, thermalImage.imageId);
      setRegistration(result);
      await loadMappingState();
    } catch (error) {
      setRegistration({ status: 'UNREGISTERED', reason: error.response?.data?.detail || 'Registration request failed' });
    } finally {
      setRegistering(false);
    }
  };

  const runAutoRegistration = async () => {
    setRegistering(true);
    setActionError('');
    try {
      const res = await autoRegisterImages(project._id);
      if (res.results?.length) setRegistration(res.results[0]);
      await loadMappingState();
    } catch (error) {
      setActionError(error.response?.data?.detail || 'Auto-registration failed.');
    } finally {
      setRegistering(false);
    }
  };

  const runAdvancedMapping = async () => {
    setAnalyzingMap(true);
    setActionError('');
    try {
      const res = await analyzeProjectMapping(project._id, {
        job_id: project.jobId || null,
        enable_cross_image_registration: rgbImages.length >= 2,
      });
      setMappingData(res);
      if (res?.panelResults?.length) setRgbResults(res.panelResults);
    } catch (error) {
      setActionError(error.response?.data?.detail || 'Mapping analysis failed.');
    } finally {
      setAnalyzingMap(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 16 }}>
        <div>
          <div style={s.pageTitle}>Panel Mapping</div>
          <div style={s.pageSub}>Model-backed localization, adaptive PCA clustering, and evidence-gated RGB–thermal registration.</div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button style={s.btnAction} disabled={analyzingMap || !rgbImages.length} onClick={runAdvancedMapping}>
            <RefreshCw size={12} /> {analyzingMap ? 'Analyzing…' : 'Run Mapping & Clustering'}
          </button>
          <button style={s.btnAction} disabled={registering || !rgbImages.length || !thermalImages.length} onClick={runAutoRegistration}>
            {registering ? 'Pairing…' : 'Auto-Pair & Align'}
          </button>
        </div>
      </div>

      {actionError && <div role="alert" style={s.errorBanner}>{actionError}</div>}

      {/* Top KPI summary */}
      <div style={s.kpiGrid}>
        {[
          { label: 'Detected Panels', value: totalPanels || '—', color: '#e2e8f0' },
          { label: 'Healthy Panels', value: aggSummary?.healthy_panels ?? '—', color: '#10b981' },
          { label: 'Unassigned Findings', value: unassignedFindings.length, color: unassignedFindings.length ? '#f59e0b' : '#94a3b8' },
          { label: 'Uncertain / Review', value: uncertainFindings.length, color: uncertainFindings.length ? '#ef4444' : '#94a3b8' },
        ].map(k => (
          <div key={k.label} style={s.kpiCard}>
            <div style={{ fontSize: 20, fontWeight: 700, color: k.color }}>{k.value}</div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{k.label}</div>
          </div>
        ))}
      </div>

      <div style={s.mapGrid}>
        {/* Thermal */}
        <div style={s.card}>
          <div style={s.cardHead}>
            <span style={s.cardTitle}>Thermal Image</span>
            {hasThermal && <span style={s.counter}>{thermalIdx + 1}/{thermalImages.length}</span>}
          </div>
          {hasThermal ? (
            <>
              {thermalUrl ? <img src={thermalUrl} alt={thermalImages[thermalIdx].imageName} style={s.mapImg} /> : <div style={s.emptyBox}>Loading protected image…</div>}
              <div style={s.navRow}>
                <button style={s.btnNav} disabled={thermalIdx === 0} onClick={() => setThermalIdx(i => i - 1)}><ChevronLeft size={12} /> Prev</button>
                <span style={s.navName}>{thermalImages[thermalIdx].imageName}</span>
                <button style={s.btnNav} disabled={thermalIdx === thermalImages.length - 1} onClick={() => setThermalIdx(i => i + 1)}>Next <ChevronRight size={12} /></button>
              </div>
            </>
          ) : <div style={s.emptyBox}>No thermal images</div>}
        </div>

        {/* Alignment controls */}
        <div style={s.arrowCol}>
          <div style={s.arrowLine} />
          <span style={s.arrowText}>→</span>
          <button style={s.btnNav} disabled={!cur || !thermalImages.length || registering} onClick={registerCurrentPair}>
            {registering ? 'Aligning…' : 'Align pair'}
          </button>
          {currentPairRegistration && (
            <div style={{ ...s.counter, color: currentPairRegistration.status === 'REGISTERED' ? '#10b981' : '#f59e0b', textAlign: 'center', marginTop: 6 }}>
              <div>{currentPairRegistration.status}</div>
              {currentPairRegistration.quality != null && (
                <div>Inliers {Math.round(currentPairRegistration.quality * 100)}%</div>
              )}
              {currentPairRegistration.mean_reprojection_error_px != null && (
                <div>Err {currentPairRegistration.mean_reprojection_error_px.toFixed(2)}px</div>
              )}
              {currentPairRegistration.status !== 'REGISTERED' && currentPairRegistration.reason && (
                <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>{currentPairRegistration.reason}</div>
              )}
            </div>
          )}
        </div>

        {/* RGB numbered */}
        <div style={s.card}>
          <div style={s.cardHead}>
            <span style={s.cardTitle}>Numbered RGB Image</span>
            {hasRgb && (
              <span style={{ ...s.counter, color: '#10b981' }}>
                {cur.panels?.length || 0} panels
                {cur.regions?.length ? ` · ${cur.regions.length} region${cur.regions.length > 1 ? 's' : ''}` : ''}
              </span>
            )}
          </div>
          {hasRgb && (cur.panels?.length || 0) > 0 ? (
            <>
              {rgbUrl && (
                <PanelOverlay
                  src={rgbUrl}
                  panels={cur.panels}
                  imageSize={cur.imageSize}
                  selectedPanel={selectedPanel}
                  onSelect={setSelectedPanel}
                  findingsByPanel={findingsByPanel}
                />
              )}
              <div style={s.navRow}>
                <button style={s.btnNav} disabled={rgbIdx === 0} onClick={() => setRgbIdx(i => i - 1)}><ChevronLeft size={12} /> Prev</button>
                <span style={s.navName}>{cur.panels?.length || 0} localized panels</span>
                <button style={s.btnNav} disabled={rgbIdx === rgbResults.length - 1} onClick={() => setRgbIdx(i => i + 1)}>Next <ChevronRight size={12} /></button>
              </div>
            </>
          ) : (
            <div style={s.emptyBox}>
              {!rgbImages.length
                ? 'No RGB images uploaded'
                : panelsLoading
                  ? 'Loading saved panel results…'
                  : cur
                    ? (cur.message || `Panel model status: ${cur.status} (0 detections)`)
                    : 'No panel result yet; run analysis first.'}
            </div>
          )}
        </div>
      </div>

      {/* Selected panel inspector */}
      {selectedPanelRecord && (
        <div style={s.inspectorCard}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#34d399' }}>
              Selected Panel: {selectedPanelRecord.panel_id} ({formatGridCoordinate(selectedPanelRecord)})
            </div>
            <button style={s.btnNav} onClick={() => setSelectedPanel(null)}>Clear selection</button>
          </div>
          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', fontSize: 12, color: '#cbd5e1' }}>
            <span>Row: <strong>{selectedPanelRecord.row_id ?? '—'}</strong></span>
            <span>Column: <strong>{selectedPanelRecord.column_id ?? '—'}</strong></span>
            <span>Region: <strong>{selectedPanelRecord.region_id ?? 1}</strong></span>
            <span>Confidence: <strong>{Math.round((selectedPanelRecord.confidence || 0) * 100)}%</strong></span>
            <span>Scope: <strong>{selectedPanelRecord.site_panel_id ? `Site (${selectedPanelRecord.site_panel_id})` : 'Image-local'}</strong></span>
            <span>Orientation: <strong>{selectedPanelRecord.orientation_degrees != null ? `${selectedPanelRecord.orientation_degrees.toFixed(1)}°` : '—'}</strong></span>
          </div>
        </div>
      )}

      {/* Stage-by-stage Mapping Quality & Uncertainty */}
      {quality && (
        <div style={s.tableCard}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, gap: 12, flexWrap: 'wrap' }}>
            <span style={s.cardTitle2}>Mapping Quality & Uncertainty Diagnostics</span>
            <span style={{ fontSize: 11, color: '#f59e0b' }}>{quality.measured_accuracy_note}</span>
          </div>
          <div style={s.qualityGrid}>
            <div style={s.qItem}>
              <div style={s.qLabel}>Panel Detection</div>
              <div style={s.qVal}>{quality.stages?.panel_detection?.mean_confidence != null ? `${Math.round(quality.stages.panel_detection.mean_confidence * 100)}% mean conf` : '—'}</div>
              <div style={s.qSub}>Partial: {quality.stages?.panel_detection?.partial_panel_count ?? 0} · Suppressed dups: {quality.stages?.panel_detection?.suppressed_duplicate_count ?? 0}</div>
            </div>
            <div style={s.qItem}>
              <div style={s.qLabel}>Clustering</div>
              <div style={s.qVal}>{quality.stages?.clustering?.array_region_count ?? 0} regions</div>
              <div style={s.qSub}>Assigned: {quality.stages?.clustering?.assigned_row_column_ratio != null ? `${Math.round(quality.stages.clustering.assigned_row_column_ratio * 100)}%` : '—'} · Missing slots est: {quality.stages?.clustering?.estimated_missing_slots ?? 0}</div>
            </div>
            <div style={s.qItem}>
              <div style={s.qLabel}>Registration</div>
              <div style={s.qVal}>{quality.stages?.registration?.registered_count ?? 0}/{quality.stages?.registration?.pair_count ?? 0} pairs</div>
              <div style={s.qSub}>Mean reproj err: {quality.stages?.registration?.mean_reprojection_error_px != null ? `${quality.stages.registration.mean_reprojection_error_px.toFixed(2)} px` : '—'}</div>
            </div>
            <div style={s.qItem}>
              <div style={s.qLabel}>Association & Dedup</div>
              <div style={s.qVal}>{quality.stages?.association?.matched_count ?? 0}/{quality.stages?.association?.total_findings ?? 0} matched</div>
              <div style={s.qSub}>Dedup: {dedup?.status || 'NOT_RUN'} · Merged: {dedup?.duplicates_merged ?? 0}</div>
            </div>
          </div>
        </div>
      )}

      {/* Findings & Panel Aggregation Tabs */}
      <div style={s.tableCard}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {[
              { id: 'all', label: `All Findings (${findings.length})` },
              { id: 'panels', label: `Panel Aggregation (${aggregatedPanels.length})` },
              { id: 'unassigned', label: `Unassigned (${unassignedFindings.length})` },
              { id: 'uncertain', label: `Uncertain / Review (${uncertainFindings.length})` },
            ].map(t => (
              <button
                key={t.id}
                style={{ ...s.tabBtn, ...(activeTab === t.id && !selectedPanel ? s.tabBtnActive : {}) }}
                onClick={() => { setSelectedPanel(null); setActiveTab(t.id); }}
              >
                {t.label}
              </button>
            ))}
          </div>
          {selectedPanel && <button style={s.btnNav} onClick={() => setSelectedPanel(null)}>Clear panel filter · {selectedPanel}</button>}
        </div>

        {activeTab === 'panels' && !selectedPanel ? (
          <table style={s.table}>
            <thead>
              <tr>{['Panel ID', 'Row / Col', 'Status', 'Findings (Thm / RGB)', 'Manual Review', 'Scope'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {aggregatedPanels.length > 0 ? aggregatedPanels.map(p => (
                <tr key={p.panel_id} style={{ cursor: 'pointer' }} onClick={() => setSelectedPanel(p.local_panel_ids?.[0] || p.panel_id)}>
                  <td style={s.td}><span style={s.panelBadge}>{p.panel_id}</span></td>
                  <td style={s.td}>{p.row_label || p.row_id || '—'} / {p.column_label || p.column_id || '—'}</td>
                  <td style={s.td}>
                    <span style={{ ...s.sevBadge, ...(p.inspection_status === 'Healthy' ? s.sevLow : s.sevHigh) }}>
                      {p.inspection_status === 'Healthy' ? <CheckCircle2 size={11} style={{ verticalAlign: 'middle', marginRight: 4 }} /> : <AlertTriangle size={11} style={{ verticalAlign: 'middle', marginRight: 4 }} />}
                      {p.inspection_status}
                    </span>
                  </td>
                  <td style={s.td}>{p.finding_count} ({p.thermal_finding_count} / {p.rgb_finding_count})</td>
                  <td style={s.td}>{p.manual_verification_status}</td>
                  <td style={s.td}>{p.identity_scope}</td>
                </tr>
              )) : (
                <tr><td colSpan={6} style={{ ...s.td, textAlign: 'center', color: '#475569' }}>No aggregated panel records yet.</td></tr>
              )}
            </tbody>
          </table>
        ) : (
          <table style={s.table}>
            <thead>
              <tr>{['Modality', 'Mapped Panel', 'Defect Type', 'Model Conf', 'Spatial Match', 'Inspection Priority'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {displayedFindings.length > 0 ? displayedFindings.map((r, i) => (
                <tr key={r.findingId || i}>
                  <td style={s.td}>{r.modality}</td>
                  <td style={s.td}>
                    <span style={s.panelBadge}>
                      {r.panelId || r.matchStatus || 'UNASSIGNED'}
                    </span>
                    {r.candidatePanelIds?.length > 1 && r.matchStatus === 'REVIEW_REQUIRED' && (
                      <div style={{ fontSize: 10, color: '#f59e0b', marginTop: 2 }}>
                        Candidates: {r.candidatePanelIds.join(', ')}
                      </div>
                    )}
                  </td>
                  <td style={s.td}>{r.defectType}</td>
                  <td style={{ ...s.td, color: '#10b981', fontWeight: 600 }}>{Math.round((r.modelConfidence || 0) * 100)}%</td>
                  <td style={s.td}>
                    {r.spatialMatchConfidence != null ? `${Math.round(r.spatialMatchConfidence * 100)}%` : '—'}
                    {r.matchStatus === 'REVIEW_REQUIRED' && <HelpCircle size={11} color="#f59e0b" style={{ marginLeft: 4, verticalAlign: 'middle' }} />}
                  </td>
                  <td style={s.td}>
                    <span style={{ ...s.sevBadge, ...(r.inspectionPriority === 'High' ? s.sevHigh : s.sevLow) }}>
                      {r.inspectionPriority || 'Unassigned'} · severity unvalidated{r.reviewRequired ? ' · Review' : ''}
                    </span>
                  </td>
                </tr>
              )) : (
                <tr><td colSpan={6} style={{ ...s.td, textAlign: 'center', color: '#475569' }}>No findings in this view</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <div style={s.footer}>
        <span style={{ fontSize: 13, color: '#64748b' }}>Total panels detected: <strong style={{ color: '#e2e8f0' }}>{totalPanels}</strong></span>
        <button style={s.btnNext} onClick={onNext}>Next — Defect Summary <ArrowRight size={14} /></button>
      </div>
    </div>
  );
}

const s = {
  pageTitle: { fontSize: 20, fontWeight: 700, marginBottom: 4 },
  pageSub: { fontSize: 13, color: '#64748b', marginBottom: 16 },
  errorBanner: { background: '#3f0a0a', border: '1px solid #991b1b', color: '#fecaca', padding: '10px 14px', borderRadius: 8, fontSize: 12.5, marginBottom: 14 },
  btnAction: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155', borderRadius: 7, fontSize: 12, fontWeight: 600, cursor: 'pointer' },
  kpiGrid: { display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 16 },
  kpiCard: { background: '#111827', border: '1px solid #1e2d45', borderRadius: 9, padding: '12px 14px', textAlign: 'center' },
  mapGrid: { display: 'grid', gridTemplateColumns: '1fr 96px 1fr', gap: 12, marginBottom: 18, alignItems: 'start' },
  card: { background: '#111827', border: '1px solid #1e2d45', borderRadius: 10, padding: 14 },
  cardHead: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  cardTitle: { fontSize: 13, fontWeight: 600, color: '#e2e8f0' },
  cardTitle2: { fontSize: 14, fontWeight: 600, color: '#e2e8f0' },
  counter: { fontSize: 11, color: '#64748b' },
  mapImg: { width: '100%', height: 260, objectFit: 'contain', borderRadius: 7, background: '#000', display: 'block' },
  navRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 },
  btnNav: { display: 'inline-flex', alignItems: 'center', gap: 3, padding: '4px 10px', background: 'transparent', color: '#94a3b8', border: '1px solid #1e2d45', borderRadius: 5, fontSize: 11, cursor: 'pointer' },
  navName: { fontSize: 11, color: '#64748b', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'center' },
  emptyBox: { height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: 13, border: '1px dashed #1e2d45', borderRadius: 7, padding: 16, textAlign: 'center' },
  arrowCol: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', paddingTop: 95 },
  arrowLine: { width: 2, height: 24, background: '#1e2d45' },
  arrowText: { fontSize: 22, color: '#6366f1', margin: '4px 0' },
  inspectorCard: { background: '#0f172a', border: '1px solid #10b981', borderRadius: 10, padding: '12px 16px', marginBottom: 16 },
  qualityGrid: { display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 },
  qItem: { background: '#0b1120', border: '1px solid #1e2d45', borderRadius: 8, padding: '10px 12px' },
  qLabel: { fontSize: 10.5, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.4, fontWeight: 600 },
  qVal: { fontSize: 14, fontWeight: 700, color: '#e2e8f0', marginTop: 4 },
  qSub: { fontSize: 11, color: '#94a3b8', marginTop: 3 },
  tableCard: { background: '#111827', border: '1px solid #1e2d45', borderRadius: 10, padding: 16, marginBottom: 16 },
  tabBtn: { padding: '5px 11px', borderRadius: 6, background: '#0b1120', border: '1px solid #1e2d45', color: '#94a3b8', fontSize: 11.5, fontWeight: 600, cursor: 'pointer' },
  tabBtnActive: { background: '#1e1b4b', borderColor: '#6366f1', color: '#e0e7ff' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { padding: '9px 12px', textAlign: 'left', fontSize: 11, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', borderBottom: '1px solid #1e2d45' },
  td: { padding: '9px 12px', fontSize: 12.5, color: '#cbd5e1', borderBottom: '1px solid #0b1120' },
  panelBadge: { background: '#0c1a3a', color: '#60a5fa', padding: '2px 8px', borderRadius: 5, fontWeight: 700, fontSize: 11 },
  sevBadge: { padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600 },
  sevHigh: { background: '#3f0a0a', color: '#f87171' },
  sevLow: { background: '#052e16', color: '#22c55e' },
  footer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 20, borderTop: '1px solid #1e2d45' },
  btnNext: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 24px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 600, cursor: 'pointer' },
};
