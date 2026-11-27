import { useRef, useState, useEffect } from 'react';
import { FolderOpen, CheckCircle, X, Image, ArrowRight, Loader } from 'lucide-react';
import { uploadImages, analyzeImages, getAnalysisJob } from '../../api';

function UploadSection({ label, files, setFiles, done, setDone }) {
  const fileRef   = useRef();
  const folderRef = useRef();
  const [progress, setProgress]   = useState(0);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging]   = useState(false);

  useEffect(() => {
    if (folderRef.current) {
      folderRef.current.setAttribute('webkitdirectory', '');
      folderRef.current.setAttribute('directory', '');
    }
  }, []);

  const handle = (list) => {
    const ok = Array.from(list).filter(f => /\.(jpg|jpeg|png|tif|tiff)$/i.test(f.name));
    if (!ok.length) return;
    setFiles(ok); setDone(false); setProgress(0); setUploading(true);
    let p = 0;
    const iv = setInterval(() => {
      p = Math.min(100, p + Math.max(2, Math.round(100 / (ok.length * 2))));
      setProgress(p);
      if (p >= 100) { clearInterval(iv); setUploading(false); setDone(true); }
    }, 80);
  };

  const clear = () => { setFiles([]); setDone(false); setProgress(0); setUploading(false); };

  return (
    <div style={s.card}>
      <div style={s.cardTitle}>{label}</div>
      <div
        style={{
          ...s.zone,
          borderColor: dragging ? '#b91c1c' : '#d9e2f0',
          background: dragging ? 'rgba(185,28,28,0.04)' : '#ffffff',
          boxShadow: dragging ? '0 0 0 3px rgba(185,28,28,0.08)' : 'none'
        }}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); handle(e.dataTransfer.files); }}
      >
        <p style={{ fontWeight: 700, marginBottom: 6, color: '#0a2545', fontSize: 25 }}>Drag & Drop folder or images here</p>
        <p style={{ color: '#55657f', fontSize: 13, marginBottom: 18 }}>or choose an option below</p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button style={s.btnPrimary} onClick={e => { e.stopPropagation(); folderRef.current.click(); }}>
            <FolderOpen size={14} /> Upload Folder
          </button>
          <button style={s.btnOutline} onClick={e => { e.stopPropagation(); fileRef.current.click(); }}>
            <Image size={14} /> Select Files
          </button>
        </div>
        <p style={{ color: '#55657f', fontSize: 11, marginTop: 12 }}>Supported: .jpg .jpeg .png .tif</p>
      </div>

      <input ref={folderRef} type="file" multiple style={{ display: 'none' }} onChange={e => handle(e.target.files)} />
      <input ref={fileRef} type="file" multiple accept=".jpg,.jpeg,.png,.tif,.tiff" style={{ display: 'none' }} onChange={e => handle(e.target.files)} />

      {(uploading || done) && files.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}>
            <span>
              {done
                ? <span style={{ color: '#0a2545', display: 'flex', alignItems: 'center', gap: 5 }}><CheckCircle size={13} color="#0a2545" /> {files.length} files ready</span>
                : `Loading ${Math.round(progress / 100 * files.length)}/${files.length}`}
            </span>
            <span style={{ color: '#55657f' }}>{progress}%</span>
          </div>
          <div style={s.progressBar}><div style={{ ...s.progressFill, width: `${progress}%` }} /></div>
        </div>
      )}

      {files.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: '#55657f' }}>{files.length} file{files.length > 1 ? 's' : ''} selected</span>
            <button style={s.btnClear} onClick={clear}>Clear All</button>
          </div>
          <div style={{ maxHeight: 160, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 5 }}>
            {files.map((f, i) => (
              <div key={i} style={s.fileRow}>
                <Image size={12} color="#0a2545" />
                <span style={s.fileName}>{f.webkitRelativePath || f.name}</span>
                <span style={{ color: '#55657f', fontSize: 11, flexShrink: 0 }}>{(f.size / 1024).toFixed(0)} KB</span>
                <button style={s.btnX} onClick={() => { const u = files.filter((_, j) => j !== i); setFiles(u); if (!u.length) clear(); }}>
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function WorkflowUpload({ project, onNext }) {
  const [thermalFiles, setThermalFiles] = useState([]);
  const [rgbFiles, setRgbFiles]         = useState([]);
  const [thermalDone, setThermalDone]   = useState(false);
  const [rgbDone, setRgbDone]           = useState(false);
  const [submitting, setSubmitting]     = useState(false);
  const [statusMsg, setStatusMsg]       = useState('');
  const [error, setError] = useState('');
  const requestIdRef = useRef(null);

  const canNext = thermalFiles.length > 0 || rgbFiles.length > 0;

  const handleConfirm = async () => {
    setSubmitting(true);
    setError('');
    const projectId = project._id;

    try {
      // Upload thermal images to backend
      let thermalImages = [];
      let rgbImages = [];
      if (thermalFiles.length > 0) {
        setStatusMsg(`Uploading ${thermalFiles.length} thermal images...`);
        thermalImages = (await uploadImages(projectId, 'thermal', thermalFiles)).images;
      }

      // Upload RGB images to backend
      if (rgbFiles.length > 0) {
        setStatusMsg(`Uploading ${rgbFiles.length} RGB images...`);
        rgbImages = (await uploadImages(projectId, 'rgb', rgbFiles)).images;
      }

      // Trigger analysis on backend
      setStatusMsg('Running defect detection...');
      if (!requestIdRef.current) requestIdRef.current = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${projectId}`;
      let job = await analyzeImages(projectId, requestIdRef.current);
      while (job.status === 'PENDING' || job.status === 'PROCESSING') {
        setStatusMsg(`Analyzing images... ${job.percentage || 0}%`);
        await new Promise(resolve => setTimeout(resolve, 700));
        job = await getAnalysisJob(projectId, job.jobId);
      }
      setStatusMsg('');
      onNext(thermalFiles, rgbFiles, { thermalImages, rgbImages, jobId: job.jobId });
      requestIdRef.current = null;
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Upload or analysis failed.');
      setStatusMsg('');
    }

    setSubmitting(false);
  };

  return (
    <div>
      <div style={s.pageTitle}>Upload Images</div>
      <div style={s.pageSub}>Upload drone-captured thermal and RGB images for <strong style={{ color: '#0a2545' }}>{project.projectName}</strong></div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 32 }}>
        <UploadSection label="Thermal Images" files={thermalFiles} setFiles={setThermalFiles} done={thermalDone} setDone={setThermalDone} />
        <UploadSection label="RGB Images"     files={rgbFiles}     setFiles={setRgbFiles}     done={rgbDone}     setDone={setRgbDone} />
      </div>

      <div style={s.footer}>
        <div>
          <span style={{ fontSize: 13, color: '#64748b' }}>
            {thermalFiles.length} thermal · {rgbFiles.length} RGB selected
          </span>
          {statusMsg && (
            <span style={{ fontSize: 12, color: '#6366f1', marginLeft: 16, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <Loader size={12} style={{ animation: 'spin 1s linear infinite' }} /> {statusMsg}
            </span>
          )}
        </div>
        <button
          style={{ ...s.btnNext, opacity: canNext && !submitting ? 1 : 0.4, cursor: canNext && !submitting ? 'pointer' : 'not-allowed' }}
          disabled={!canNext || submitting}
          onClick={handleConfirm}
        >
          {submitting ? <><Loader size={14} style={{ animation: 'spin 1s linear infinite' }} /> Processing...</> : <>Confirm & Continue <ArrowRight size={14} /></>}
        </button>
      </div>
      {error && <div role="alert" style={{ color: '#b91c1c', marginTop: 14, fontSize: 13 }}>{error}</div>}
      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}

const s = {
  pageTitle: { fontSize: 20, fontWeight: 700, marginBottom: 4, color: '#0a2545' },
  pageSub: { fontSize: 13, color: '#55657f', marginBottom: 24 },
  card: { background: '#ffffff', border: '1px solid #d9e2f0', borderRadius: 10, padding: 18, boxShadow: '0 2px 8px rgba(10,37,69,0.04)' },
  cardTitle: { fontSize: 16, fontWeight: 700, marginBottom: 14, color: '#0a2545' },
  zone: { border: '2px dashed', borderRadius: 9, padding: '32px 20px', textAlign: 'center', transition: 'border-color 0.2s', background: '#ffffff' },
  btnPrimary: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 18px', background: '#0a2545', color: '#fff', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 700, cursor: 'pointer' },
  btnOutline: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 18px', background: 'transparent', color: '#0a2545', border: '1px solid #d9e2f0', borderRadius: 7, fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  btnClear: { padding: '3px 10px', background: 'transparent', color: '#b91c1c', border: '1px solid #f6b3b3', borderRadius: 5, fontSize: 11, cursor: 'pointer' },
  btnX: { background: 'none', border: 'none', cursor: 'pointer', color: '#55657f', display: 'flex', padding: 0, flexShrink: 0 },
  fileRow: { display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', background: '#f8fafc', borderRadius: 6, fontSize: 12, border: '1px solid #edf3fa' },
  fileName: { flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#0a2545' },
  progressBar: { height: 5, background: '#edf3ff', borderRadius: 3, overflow: 'hidden' },
  progressFill: { height: '100%', background: 'linear-gradient(90deg,#0a2545,#b91c1c)', borderRadius: 3, transition: 'width 0.3s' },
  footer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 20, borderTop: '1px solid #d9e2f0' },
  btnNext: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 24px', background: '#0a2545', color: '#fff', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 600 },
};
