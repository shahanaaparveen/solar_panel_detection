import { useState, useEffect } from 'react';
import Login from './pages/Login';
import ProjectsPage from './pages/ProjectsPage';
import NewProjectInfo from './pages/NewProjectInfo';
import ProjectDetail from './pages/ProjectDetail';
import WorkflowLayout from './pages/WorkflowLayout';
import AllReports from './pages/AllReports';
import { getProjects, createProject, deleteProject } from './api';
import './App.css';

export default function App() {
  const [isLoggedIn, setIsLoggedIn]     = useState(false);
  const [screen, setScreen]             = useState('projects');
  const [projects, setProjects]         = useState([]);
  const [currentProject, setCurrentProject] = useState(null);
  const [workflowStep, setWorkflowStep] = useState(1);
  const [loading, setLoading]           = useState(false);

  // Load projects from MongoDB on mount
  useEffect(() => {
    if (isLoggedIn) fetchProjects();
  }, [isLoggedIn]);

  const fetchProjects = async () => {
    try {
      const data = await getProjects();
      setProjects(data);
    } catch {
      // backend not running yet — use local state
    }
  };

  const handleCreateProject = async (info) => {
    setLoading(true);
    try {
      const proj = await createProject(info);
      setProjects(prev => [proj, ...prev]);
      setCurrentProject(proj);
    } catch {
      // fallback: create locally
      const proj = {
        _id: Date.now().toString(), ...info,
        status: 'In Progress',
        createdAt: new Date().toISOString(),
        date: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
        thermalImages: [], rgbImages: [],
      };
      setProjects(prev => [proj, ...prev]);
      setCurrentProject(proj);
    }
    setWorkflowStep(1);
    setScreen('workflow');
    setLoading(false);
  };

  const handleDeleteProject = async (id) => {
    try {
      await deleteProject(id);
    } catch (err) {
      console.error('Failed to delete project on backend', err);
    }
    setProjects(prev => prev.filter(p => (p._id || p.id) !== id));
  };

  const handleUpdateProject = (updated) => {
    setCurrentProject(updated);
    setProjects(prev => prev.map(p => (p._id || p.id) === (updated._id || updated.id) ? updated : p));
  };

  if (!isLoggedIn) return <Login onLogin={() => setIsLoggedIn(true)} />;

  if (screen === 'projects') return (
    <ProjectsPage
      projects={projects}
      onNewProject={() => setScreen('newproject')}
      onOpenProject={p => { setCurrentProject(p); setScreen('detail'); }}
      onViewReports={() => setScreen('allreports')}
      onLogout={() => setIsLoggedIn(false)}
      onDeleteProject={handleDeleteProject}
    />
  );

  if (screen === 'newproject') return (
    <NewProjectInfo onBack={() => setScreen('projects')} onCreate={handleCreateProject} loading={loading} />
  );

  if (screen === 'detail') return (
    <ProjectDetail
      project={currentProject}
      onBack={() => setScreen('projects')}
      onContinue={() => { setWorkflowStep(1); setScreen('workflow'); }}
    />
  );

  if (screen === 'allreports') return (
    <AllReports projects={projects} onBack={() => setScreen('projects')} />
  );

  if (screen === 'workflow') return (
    <WorkflowLayout
      project={currentProject}
      step={workflowStep}
      onStepChange={setWorkflowStep}
      onUpdateProject={handleUpdateProject}
      onBackToProjects={() => { setScreen('projects'); fetchProjects(); }}
    />
  );

  return null;
}
