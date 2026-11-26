import { useState } from 'react';
import { Eye, EyeOff, User, Lock } from 'lucide-react';
import bgImage from '../assets/fbg1.png';

export default function Login({ onLogin }) {
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(true);
  const [form, setForm] = useState({ email: '', password: '' });

  return (
    <div style={styles.page}>
      {/* Full-screen background */}
      <div style={styles.bg} />
      {/* Dark gradient overlay — stronger on left, fades right */}
      <div style={styles.overlay} />

      {/* TOP SECTION: branding left + login card right */}
      <div style={styles.top}>
        {/* LEFT — logo + tagline */}
        <div style={styles.left}>
          <h1 style={styles.brand}>SOLAR INSPECT</h1>
          <p style={styles.brandSub1}>AI POWERED SOLAR PANEL</p>
          <p style={styles.brandSub2}>THERMAL INSPECTION &amp; ANALYSIS SYSTEM</p>

          <p style={styles.tagline}>
            Detect. Analyze. Report.<br />
            All in One Intelligent Platform
          </p>
        </div>

        {/* RIGHT — login card */}
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>Welcome Back!</h2>
          <p style={styles.cardSub}>Sign in to continue</p>

          <div style={styles.formGroup}>
            <label style={styles.label}>Username / Email</label>
            <div style={styles.inputWrap}>
              <User size={15} color="#64748b" style={styles.inputIcon} />
              <input
                id="email-input"
                style={styles.input}
                placeholder="Enter your email"
                value={form.email}
                onChange={e => setForm({ ...form, email: e.target.value })}
              />
            </div>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Password</label>
            <div style={styles.inputWrap}>
              <Lock size={15} color="#64748b" style={styles.inputIcon} />
              <input
                id="password-input"
                style={{ ...styles.input, paddingRight: 40 }}
                type={show ? 'text' : 'password'}
                placeholder="Enter your password"
                value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
              />
              <button onClick={() => setShow(!show)} style={styles.eyeBtn}>
                {show ? <EyeOff size={15} color="#64748b" /> : <Eye size={15} color="#64748b" />}
              </button>
            </div>
          </div>

          <div style={styles.rememberRow}>
            <label style={styles.rememberLabel}>
              <div
                style={{ ...styles.checkbox, background: remember ? '#6366f1' : 'transparent' }}
                onClick={() => setRemember(!remember)}
              >
                {remember && <span style={{ color: '#fff', fontSize: 10, lineHeight: 1 }}>✓</span>}
              </div>
              Remember me
            </label>
            <span style={styles.forgot}>Forgot Password?</span>
          </div>

          <button id="login-btn" style={styles.loginBtn} onClick={onLogin}>Login</button>

          <p style={styles.signupText}>
            Don't have an account?{' '}
            <span style={styles.signupLink}>Sign Up</span>
          </p>
        </div>
      </div>

      {/* BOTTOM — 4 feature icons */}
      <div style={styles.bottom}>
        {[
          {
            icon: (
              <svg viewBox="0 0 40 40" width="38" height="38" fill="none">
                <polygon points="20,2 38,11 38,29 20,38 2,29 2,11" stroke="white" strokeWidth="1.5" fill="none"/>
                <text x="20" y="24" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">AI</text>
              </svg>
            ),
            title: 'AI Defect Detection',
            desc: 'Automatically detect multiple defects in thermal images',
          },
          {
            icon: (
              <svg viewBox="0 0 40 40" width="38" height="38" fill="none">
                <polygon points="20,2 38,11 38,29 20,38 2,29 2,11" stroke="white" strokeWidth="1.5" fill="none"/>
                <path d="M20 26 L20 16 M16 20 L20 16 L24 20" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M14 28 Q14 26 16 26 L24 26 Q26 26 26 28" stroke="white" strokeWidth="1.5" strokeLinecap="round" fill="none"/>
              </svg>
            ),
            title: 'Multi Image Upload',
            desc: 'Upload folders of thermal images in bulk',
          },
          {
            icon: (
              <svg viewBox="0 0 40 40" width="38" height="38" fill="none">
                <polygon points="20,2 38,11 38,29 20,38 2,29 2,11" stroke="white" strokeWidth="1.5" fill="none"/>
                <rect x="12" y="12" width="16" height="16" rx="1" stroke="white" strokeWidth="1.2" fill="none"/>
                <line x1="12" y1="17" x2="28" y2="17" stroke="white" strokeWidth="1"/>
                <line x1="12" y1="22" x2="28" y2="22" stroke="white" strokeWidth="1"/>
                <line x1="17" y1="12" x2="17" y2="28" stroke="white" strokeWidth="1"/>
                <line x1="22" y1="12" x2="22" y2="28" stroke="white" strokeWidth="1"/>
              </svg>
            ),
            title: 'Panel Mapping',
            desc: 'Map defects with numbered solar panels',
          },
          {
            icon: (
              <svg viewBox="0 0 40 40" width="38" height="38" fill="none">
                <polygon points="20,2 38,11 38,29 20,38 2,29 2,11" stroke="white" strokeWidth="1.5" fill="none"/>
                <rect x="13" y="10" width="14" height="18" rx="1.5" stroke="white" strokeWidth="1.2" fill="none"/>
                <line x1="16" y1="15" x2="24" y2="15" stroke="white" strokeWidth="1"/>
                <line x1="16" y1="18" x2="24" y2="18" stroke="white" strokeWidth="1"/>
                <line x1="16" y1="21" x2="21" y2="21" stroke="white" strokeWidth="1"/>
              </svg>
            ),
            title: 'Detailed Reports',
            desc: 'Generate professional reports with images and insights',
          },
        ].map((f, i, arr) => (
          <div key={f.title} style={{ ...styles.feature, borderRight: i < arr.length - 1 ? '1px solid rgba(255,255,255,0.12)' : 'none' }}>
            <div style={styles.featureIcon}>{f.icon}</div>
            <div style={styles.featureTitle}>{f.title}</div>
            <div style={styles.featureDesc}>{f.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  page: {
    width: '100vw',
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    overflow: 'hidden',
    fontFamily: "'Segoe UI', sans-serif",
  },
  bg: {
    position: 'absolute',
    inset: 0,
    backgroundImage: `url(${bgImage})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center 40%',
    zIndex: 0,
  },
  overlay: {
    position: 'absolute',
    inset: 0,
    background: 'linear-gradient(to right, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.15) 55%, rgba(0,0,0,0.05) 100%)',
    zIndex: 1,
  },
  top: {
    position: 'relative',
    zIndex: 2,
    flex: 1,
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    padding: '48px 60px 0 60px',
  },
  left: {
    flex: 1,
    paddingTop: 8,
  },
  logoIcon: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    marginBottom: 16,
    fontSize: 52,
    lineHeight: 1,
  },
  sun: { fontSize: 56 },
  panel: { fontSize: 44, marginLeft: -8 },
  brand: {
    fontSize: 64,
    fontWeight: 900,
    color: '#ffffff',
    letterSpacing: 3,
    lineHeight: 1,
    marginBottom: 6,
    textShadow: '0 2px 24px rgba(0,0,0,0.8), 0 1px 4px rgba(0,0,0,0.9)',
  },
  brandSub1: {
    fontSize: 20,
    fontWeight: 700,
    color: '#f59e0b',
    letterSpacing: 2,
    marginBottom: 2,
    textShadow: '0 1px 8px rgba(0,0,0,0.7)',
  },
  brandSub2: {
    fontSize: 18,
    fontWeight: 600,
    color: '#ffffff',
    letterSpacing: 1.5,
    marginBottom: 28,
    textShadow: '0 1px 8px rgba(0,0,0,0.7)',
  },
  tagline: {
    fontSize: 18,
    color: 'rgba(255,255,255,0.95)',
    lineHeight: 1.7,
    textShadow: '0 1px 8px rgba(0,0,0,0.7)',
  },
  card: {
    width: 360,
    background: 'rgba(18,24,42,0.92)',
    backdropFilter: 'blur(16px)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 16,
    padding: '36px 32px',
    flexShrink: 0,
  },
  cardTitle: {
    fontSize: 22,
    fontWeight: 700,
    color: '#ffffff',
    textAlign: 'center',
    marginBottom: 4,
  },
  cardSub: {
    fontSize: 13,
    color: '#94a3b8',
    textAlign: 'center',
    marginBottom: 28,
  },
  formGroup: { marginBottom: 16 },
  label: {
    display: 'block',
    fontSize: 12.5,
    color: '#cbd5e1',
    marginBottom: 6,
    fontWeight: 500,
  },
  inputWrap: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
  },
  inputIcon: {
    position: 'absolute',
    left: 12,
    pointerEvents: 'none',
  },
  input: {
    width: '100%',
    padding: '11px 14px 11px 36px',
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 8,
    color: '#e2e8f0',
    fontSize: 13.5,
    outline: 'none',
    fontFamily: 'inherit',
  },
  eyeBtn: {
    position: 'absolute',
    right: 12,
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    padding: 0,
  },
  rememberRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 20,
    marginTop: 4,
  },
  rememberLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 13,
    color: '#cbd5e1',
    cursor: 'pointer',
    userSelect: 'none',
  },
  checkbox: {
    width: 16,
    height: 16,
    border: '2px solid #6366f1',
    borderRadius: 4,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    flexShrink: 0,
  },
  forgot: {
    fontSize: 13,
    color: '#6366f1',
    cursor: 'pointer',
    fontWeight: 500,
  },
  loginBtn: {
    width: '100%',
    padding: '13px',
    background: '#6366f1',
    border: 'none',
    borderRadius: 8,
    color: '#fff',
    fontSize: 15,
    fontWeight: 700,
    cursor: 'pointer',
    letterSpacing: 0.5,
    transition: 'background 0.2s',
    fontFamily: 'inherit',
  },
  signupText: {
    textAlign: 'center',
    marginTop: 16,
    fontSize: 13,
    color: '#64748b',
  },
  signupLink: {
    color: '#6366f1',
    cursor: 'pointer',
    fontWeight: 600,
  },
  bottom: {
    position: 'relative',
    zIndex: 2,
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    background: 'rgba(0,0,0,0.52)',
    backdropFilter: 'blur(6px)',
    borderTop: '1px solid rgba(255,255,255,0.1)',
    padding: '24px 60px',
  },
  feature: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
    padding: '0 24px',
    gap: 10,
  },
  featureIcon: {
    marginBottom: 4,
    opacity: 0.9,
  },
  featureTitle: {
    fontSize: 15,
    fontWeight: 700,
    color: '#ffffff',
  },
  featureDesc: {
    fontSize: 12.5,
    color: 'rgba(255,255,255,0.55)',
    lineHeight: 1.5,
  },
};
