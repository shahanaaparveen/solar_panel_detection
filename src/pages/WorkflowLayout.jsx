import { Upload, Cpu, GitMerge, BarChart2, Eye, FileText, CheckCircle, ArrowLeft } from 'lucide-react';
import BrandLogo from '../components/BrandLogo';
import WorkflowUpload from './workflow/WorkflowUpload';
import WorkflowAnalysis from './workflow/WorkflowAnalysis';
import WorkflowMapping from './workflow/WorkflowMapping';
import WorkflowSummary from './workflow/WorkflowSummary';
import WorkflowReportPreview from './workflow/WorkflowReportPreview';
import WorkflowReports from './workflow/WorkflowReports';

const steps = [
  { id: 1, label: 'Upload Images',    icon: Upload },
  { id: 2, label: 'Image Analysis',   icon: Cpu },
  { id: 3, label: 'Panel Mapping',    icon: GitMerge },
  { id: 4, label: 'Defect Summary',   icon: BarChart2 },
  { id: 5, label: 'Report Preview',   icon: Eye },
  { id: 6, label: 'Reports',          icon: FileText },
];

export default function WorkflowLayout({ project, step, onStepChange, onUpdateProject, onBackToProjects }) {
  const renderStep = () => {
    switch (step) {
      case 1: return <WorkflowUpload project={project} onNext={(t, r) => { onUpdateProject({ ...project, thermalFiles: t, rgbFiles: r }); onStepChange(2); }} />;
      case 2: return <WorkflowAnalysis project={project} onNext={() => onStepChange(3)} />;
      case 3: return <WorkflowMapping project={project} onUpdateProject={onUpdateProject} onNext={() => onStepChange(4)} />;
      case 4: return <WorkflowSummary project={project} onNext={() => onStepChange(5)} />;
      case 5: return <WorkflowReportPreview project={project} onUpdateProject={onUpdateProject} onNext={() => onStepChange(6)} />;
      case 6: return <WorkflowReports project={project} onBackToProjects={onBackToProjects} />;
      default: return null;
    }
  };

  return (
    <div style={s.page}>
      {/* Topbar */}
      <div style={s.topbar}>
        <div style={s.logo}><BrandLogo /></div>
        <div style={s.projName}>{project.projectName}</div>
        <button style={s.btnBack} onClick={onBackToProjects}><ArrowLeft size={13} /> Projects</button>
      </div>

      <div style={s.body}>
        {/* Left step panel */}
        <div style={s.leftPanel}>
          <div style={s.panelTitle}>Workflow</div>
          {steps.map(st => {
            const Icon = st.icon;
            const done = st.id < step;
            const active = st.id === step;
            return (
              <div
                key={st.id}
                style={{ ...s.stepItem, ...(active ? s.stepActive : done ? s.stepDone : {}) }}
                onClick={() => st.id <= step && onStepChange(st.id)}
              >
                <div style={{ ...s.stepNum, ...(active ? s.stepNumActive : done ? s.stepNumDone : {}) }}>
                  {done ? <CheckCircle size={14} /> : <Icon size={14} />}
                </div>
                <span>{st.label}</span>
              </div>
            );
          })}
        </div>

        {/* Main content */}
        <div style={s.main}>{renderStep()}</div>
      </div>
    </div>
  );
}

const s = {
  page: { minHeight: '100vh', background: '#ffffff', color: '#0a2545', fontFamily: "'Segoe UI',sans-serif", display: 'flex', flexDirection: 'column' },
  topbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 28px', background: '#ffffff', borderBottom: '1px solid #d9e2f0' },
  logo: { display: 'flex', alignItems: 'center', gap: 8 },
  projName: { fontSize: 13, color: '#55657f', fontWeight: 500 },
  btnBack: { display: 'inline-flex', alignItems: 'center', gap: 5, padding: '6px 13px', background: 'transparent', color: '#0a2545', border: '1px solid #d9e2f0', borderRadius: 7, fontSize: 12, cursor: 'pointer' },
  body: { flex: 1, display: 'flex', overflow: 'hidden' },
  leftPanel: { width: 210, background: '#ffffff', borderRight: '1px solid #d9e2f0', padding: '20px 10px', display: 'flex', flexDirection: 'column', gap: 2, flexShrink: 0 },
  panelTitle: { fontSize: 10, color: '#55657f', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, padding: '0 10px', marginBottom: 10 },
  stepItem: { display: 'flex', alignItems: 'center', gap: 9, padding: '9px 12px', borderRadius: 7, fontSize: 12.5, color: '#55657f', cursor: 'default' },
  stepActive: { background: '#ecf3ff', color: '#0a2545', cursor: 'pointer' },
  stepDone: { color: '#0a2545', cursor: 'pointer' },
  stepNum: { width: 22, height: 22, borderRadius: '50%', background: '#d9e2f0', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  stepNumActive: { background: '#0a2545', color: '#fff' },
  stepNumDone: { background: '#b91c1c', color: '#fff' },
  main: { flex: 1, overflowY: 'auto', padding: '28px 36px', background: '#ffffff' },
};
