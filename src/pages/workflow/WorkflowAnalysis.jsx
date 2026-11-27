import { useState, useEffect, useRef } from 'react';
import { ChevronLeft, ChevronRight, ArrowRight, Loader } from 'lucide-react';
import { getAnalysisJob, getDetections, retryAnalysis, getProjectImageObjectUrl } from '../../api';

// Draw bounding boxes + labels on canvas over the image
function AnnotatedImage({ src, detections }) {
  const canvasRef = useRef();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const img = new window.Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      canvas.width  = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);

      detections.forEach(d => {
        const { x, y, w, h, label, confidence, color } = d;

        // Bounding box
        ctx.strokeStyle = color || '#ef4444';
        ctx.lineWidth   = Math.max(2, img.naturalWidth / 300);
        ctx.strokeRect(x, y, w, h);

        // Semi-transparent fill
        ctx.fillStyle = (color || '#ef4444') + '22';
        ctx.fillRect(x, y, w, h);

        // Label background
        const fontSize = Math.max(11, img.naturalWidth / 55);
        ctx.font = `bold ${fontSize}px Segoe UI, sans-serif`;
        const text  = `${label} ${Math.round(confidence * 100)}%`;
        const tw    = ctx.measureText(text).width;
        const pad   = 4;
        const lh    = fontSize + pad * 2;
        const lx    = x;
        const ly    = y - lh < 0 ? y : y - lh;

        ctx.fillStyle = color || '#ef4444';
        ctx.beginPath();
        ctx.roundRect(lx, ly, tw + pad * 2, lh, 3);
        ctx.fill();

        // Label text
        ctx.fillStyle = '#fff';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, lx + pad, ly + lh / 2);
      });
    };
    img.src = src;
  }, [src, detections]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: '100%', maxHeight: 340, objectFit: 'contain', display: 'block', borderRadius: 8, background: '#000' }}
    />
  );
}

export default function WorkflowAnalysis({ project, onNext }) {
  const [thermalData, setThermalData] = useState([]);
  const [rgbData, setRgbData]         = useState([]);
  const [thermalIdx, setThermalIdx]   = useState(0);
  const [rgbIdx, setRgbIdx]           = useState(0);
  const [thermalUrls, setThermalUrls] = useState([]);
  const [rgbUrls, setRgbUrls]         = useState([]);
  const [tab, setTab]                 = useState('thermal');
  const [job, setJob] = useState(null);
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState('');

  // Prefer persisted uploads so the analysis view remains available after navigation.
  useEffect(() => {
    let disposed = false;
    const objectUrls = [];
    const makeItems = async (records, localFiles) => {
      if (records?.length) return Promise.all(records.map(async record => {
        const url = await getProjectImageObjectUrl(project._id, record.imageId);
        objectUrls.push(url);
        return { url, name: record.imageName, imageId: record.imageId };
      }));
      return (localFiles || []).map(file => {
        const url = URL.createObjectURL(file);
        objectUrls.push(url);
        return { url, name: file.name, local: true };
      });
    };
    Promise.allSettled([makeItems(project.thermalImages, project.thermalFiles), makeItems(project.rgbImages, project.rgbFiles)])
      .then(results => {
        if (results.some(result => result.status === 'rejected')) throw results.find(result => result.status === 'rejected').reason;
        const [thermal, rgb] = results.map(result => result.value);
        if (disposed) objectUrls.forEach(URL.revokeObjectURL);
        else { setThermalUrls(thermal); setRgbUrls(rgb); }
      })
      .catch(() => {
        objectUrls.forEach(URL.revokeObjectURL);
        objectUrls.length = 0;
        if (!disposed) { setThermalUrls([]); setRgbUrls([]); }
      });
    return () => { disposed = true; objectUrls.forEach(URL.revokeObjectURL); };
  }, [project._id, project.thermalImages, project.rgbImages, project.thermalFiles, project.rgbFiles]);

  // Fetch detections from MongoDB
  useEffect(() => {
    if (!project._id) return;
    getDetections(project._id, 'thermal', project.jobId).then(setThermalData).catch(() => setThermalData([]));
    getDetections(project._id, 'rgb', project.jobId).then(setRgbData).catch(() => setRgbData([]));
    if (project.jobId) getAnalysisJob(project._id, project.jobId).then(setJob).catch(() => setJob(null));
  }, [project._id, project.jobId]);

  const refreshResults = async () => {
    const [thermal, rgb] = await Promise.all([
      getDetections(project._id, 'thermal', project.jobId),
      getDetections(project._id, 'rgb', project.jobId),
    ]);
    setThermalData(thermal);
    setRgbData(rgb);
  };

  const retryIncomplete = async () => {
    setRetrying(true);
    setRetryError('');
    try {
      let current = await retryAnalysis(project._id, project.jobId);
      setJob(current);
      while (current.status === 'PENDING' || current.status === 'PROCESSING') {
        await new Promise(resolve => setTimeout(resolve, 700));
        current = await getAnalysisJob(project._id, project.jobId);
        setJob(current);
      }
      await refreshResults();
    } catch (error) {
      setRetryError(error.response?.data?.detail || error.message || 'Retry failed.');
    } finally {
      setRetrying(false);
    }
  };

  const currentList  = tab === 'thermal' ? thermalUrls : rgbUrls;
  const currentData  = tab === 'thermal' ? thermalData : rgbData;
  const currentIdx   = tab === 'thermal' ? thermalIdx  : rgbIdx;
  const setIdx       = tab === 'thermal' ? setThermalIdx : setRgbIdx;
  const currentItem  = currentList[currentIdx];
  const currentDet   = currentData[currentIdx];

  const totalDefects = [...thermalData, ...rgbData].filter(d => d.status === 'COMPLETED').reduce((s, d) => s + (d.defectCount || 0), 0);
  const modelUnavailable = ['MODEL_UNAVAILABLE', 'MODEL_ERROR'].includes(currentDet?.status);

  return (
    <div>
      <div style={s.pageTitle}>Image Analysis — Defect Detection</div>
      <div style={s.pageSub}>All uploaded images with AI-detected defect annotations</div>
      {job && <div role="status" style={{ ...s.jobNotice, borderColor: job.status === 'COMPLETED' ? '#14532d' : '#713f12' }}>
        <span>Job {job.status} · {job.completedImages || 0}/{job.totalImages} images processed · {job.percentage || 0}%</span>
        {['FAILED', 'PARTIALLY_COMPLETED'].includes(job.status) && <button style={s.btnNav} disabled={retrying} onClick={retryIncomplete}>{retrying ? <><Loader size={12} /> Retrying</> : 'Retry incomplete images'}</button>}
      </div>}
      {retryError && <div role="alert" style={{ color: '#f87171', marginBottom: 12, fontSize: 12 }}>{retryError}</div>}

      {/* Tabs */}
      <div style={s.tabs}>
        <button style={{ ...s.tab, ...(tab === 'thermal' ? s.tabActive : {}) }} onClick={() => setTab('thermal')}>
          Thermal Images ({thermalUrls.length})
        </button>
        <button style={{ ...s.tab, ...(tab === 'rgb' ? s.tabActive : {}) }} onClick={() => setTab('rgb')}>
          RGB Images ({rgbUrls.length})
        </button>
      </div>

      {/* Thumbnail strip */}
      {currentList.length > 0 && (
        <div style={s.thumbStrip}>
          {currentList.map((item, i) => {
            const det = currentData[i];
            return (
              <div key={i} style={{ ...s.thumb, outline: i === currentIdx ? '2px solid #6366f1' : 'none' }} onClick={() => setIdx(i)}>
                <img src={item.url} alt="" style={s.thumbImg} />
                {det?.defectCount > 0 && (
                  <div style={s.thumbBadge}>{det.defectCount}</div>
                )}
                <div style={s.thumbName}>{item.name}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Main annotated viewer */}
      {currentItem ? (
        <div style={s.viewer}>
          <div style={s.viewerHeader}>
            <button style={s.btnNav} disabled={currentIdx === 0} onClick={() => setIdx(i => i - 1)}>
              <ChevronLeft size={13} /> Prev
            </button>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontWeight: 600, fontSize: 13 }}>{currentItem.name}</div>
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                {currentIdx + 1} / {currentList.length} &nbsp;·&nbsp;
                <span style={{ color: modelUnavailable ? '#f59e0b' : currentDet?.defectCount > 0 ? '#ef4444' : '#22c55e' }}>
                  {modelUnavailable ? 'Model unavailable' : currentDet?.status === 'IMAGE_ERROR' ? 'Image processing failed' : currentDet?.status === 'COMPLETED' ? `${currentDet.defectCount} detections` : 'Awaiting analysis'}
                </span>
              </div>
            </div>
            <button style={s.btnNav} disabled={currentIdx === currentList.length - 1} onClick={() => setIdx(i => i + 1)}>
              Next <ChevronRight size={13} />
            </button>
          </div>

          <AnnotatedImage
            src={currentItem.url}
            detections={currentDet?.detections || []}
          />
          {modelUnavailable && <div role="status" style={{ color: '#fbbf24', padding: '10px 2px', fontSize: 12 }}>{currentDet.message || 'No trained model is configured for this modality.'}</div>}
          {currentDet?.modelId && <div style={{ color: '#64748b', paddingTop: 8, fontSize: 11 }}>Model: {currentDet.modelId} · Version: {currentDet.modelVersion || 'unknown'} · {currentDet.inferenceMs ? `${currentDet.inferenceMs.toFixed(0)} ms` : 'inference unavailable'}</div>}
          {tab === 'thermal' && currentDet?.thermalMetrics && <div style={{ color: '#64748b', paddingTop: 6, fontSize: 11 }}>{currentDet.thermalMetrics.status === 'RAW_PIXEL_STATISTICS' ? `Raw pixel values · min ${currentDet.thermalMetrics.minimum.toFixed(1)} · max ${currentDet.thermalMetrics.maximum.toFixed(1)} · mean ${currentDet.thermalMetrics.mean.toFixed(1)} (not calibrated temperature)` : 'Radiometric temperature data unavailable'}</div>}

          {/* Detections list for current image */}
          {currentDet?.detections?.length > 0 && (
            <div style={s.detList}>
              {currentDet.detections.map((d, i) => (
                <div key={i} style={{ ...s.detItem, borderLeft: `3px solid ${d.color}` }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: d.color, flexShrink: 0 }} />
                  <span style={{ flex: 1, fontWeight: 500 }}>{d.label}</span>
                  <span style={{ ...s.sevBadge, ...(d.inspection_priority === 'High' ? s.sevH : d.inspection_priority === 'Medium' ? s.sevM : s.sevL) }}>{d.inspection_priority || 'Priority unassigned'}</span>
                  <span style={{ color: '#10b981', fontWeight: 600, fontSize: 12 }}>{Math.round(d.confidence * 100)}%</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div style={s.empty}>

          <div style={{ color: '#64748b', fontSize: 14 }}>No {tab} images uploaded.</div>
        </div>
      )}

      <div style={s.footer}>
        <div style={{ fontSize: 13, color: '#64748b' }}>
          Total defects detected: <strong style={{ color: totalDefects > 0 ? '#ef4444' : '#22c55e' }}>{totalDefects}</strong>
          &nbsp;·&nbsp; Thermal: {thermalUrls.length} · RGB: {rgbUrls.length}
        </div>
        <button style={s.btnNext} onClick={onNext}>
          Next — Panel Mapping <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}

const s = {
  pageTitle: { fontSize: 20, fontWeight: 700, marginBottom: 4 },
  pageSub: { fontSize: 13, color: '#64748b', marginBottom: 20 },
  jobNotice: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, background: '#111827', border: '1px solid', borderRadius: 8, color: '#cbd5e1', fontSize: 12, padding: '10px 12px', marginBottom: 14 },
  tabs: { display: 'flex', gap: 8, marginBottom: 16 },
  tab: { padding: '8px 20px', background: '#111827', border: '1px solid #1e2d45', borderRadius: 7, color: '#64748b', fontSize: 13, cursor: 'pointer', fontWeight: 500 },
  tabActive: { background: '#1a2740', color: '#e2e8f0', borderColor: '#6366f1' },
  thumbStrip: { display: 'flex', gap: 10, overflowX: 'auto', paddingBottom: 10, marginBottom: 16 },
  thumb: { flexShrink: 0, width: 100, background: '#111827', border: '1px solid #1e2d45', borderRadius: 7, overflow: 'hidden', cursor: 'pointer', position: 'relative' },
  thumbImg: { width: '100%', height: 70, objectFit: 'cover', display: 'block' },
  thumbBadge: { position: 'absolute', top: 4, right: 4, background: '#ef4444', color: '#fff', fontSize: 10, fontWeight: 700, padding: '1px 5px', borderRadius: 10 },
  thumbName: { padding: '4px 6px', fontSize: 9, color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  viewer: { background: '#111827', border: '1px solid #1e2d45', borderRadius: 10, padding: 14, marginBottom: 20 },
  viewerHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  btnNav: { display: 'inline-flex', alignItems: 'center', gap: 4, padding: '5px 12px', background: 'transparent', color: '#94a3b8', border: '1px solid #1e2d45', borderRadius: 6, fontSize: 12, cursor: 'pointer' },
  detList: { display: 'flex', flexDirection: 'column', gap: 6, marginTop: 12 },
  detItem: { display: 'flex', alignItems: 'center', gap: 10, padding: '7px 12px', background: '#0b1120', borderRadius: 6, fontSize: 12 },
  sevBadge: { padding: '2px 8px', borderRadius: 10, fontSize: 10, fontWeight: 600 },
  sevH: { background: '#3f0a0a', color: '#f87171' },
  sevM: { background: '#431407', color: '#fb923c' },
  sevL: { background: '#052e16', color: '#22c55e' },
  empty: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 200, color: '#334155' },
  footer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 20, borderTop: '1px solid #1e2d45' },
  btnNext: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 24px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 600, cursor: 'pointer' },
};
