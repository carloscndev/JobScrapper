import { useEffect, useState } from "react";
import { createApiClient, type HealthStatus } from "./api/client";
import "./styles.css";

type Section = "profile" | "preferences";
type WorkMode = "Remoto" | "Híbrido" | "Presencial";

interface ProfileDraft {
  name: string;
  headline: string;
  skills: string;
  experience: string;
  languages: string;
  education: string;
  locations: string;
  mode: WorkMode;
  authorization: string;
  minSalary: string;
  maxSalary: string;
  weightSkills: number;
  weightExperience: number;
  weightLocation: number;
  weightMode: number;
}

const initialDraft: ProfileDraft = {
  name: "Carlos Castañeda",
  headline: "Senior Software Engineer",
  skills: "Python, TypeScript, React, FastAPI, SQL",
  experience: "Diseño de APIs y productos web durante 8 años.",
  languages: "Español (nativo), Inglés (C1)",
  education: "Ingeniería en Sistemas Computacionales",
  locations: "Ciudad de México, Guadalajara, Remoto (USA)",
  mode: "Híbrido",
  authorization: "México; autorizado para trabajar con equipos de USA",
  minSalary: "55000",
  maxSalary: "90000",
  weightSkills: 40,
  weightExperience: 30,
  weightLocation: 20,
  weightMode: 10,
};

const apiClient = createApiClient();

function App() {
  const [section, setSection] = useState<Section>("profile");
  const [draft, setDraft] = useState<ProfileDraft>(initialDraft);
  const [health, setHealth] = useState<HealthStatus>("unavailable");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [saved, setSaved] = useState(false);
  const [cvName, setCvName] = useState("CV_Carlos_Castaneda.pdf");

  const refreshHealth = async () => {
    setIsRefreshing(true);
    try {
      const response = await apiClient.getHealth();
      setHealth(response.status === "ok" ? "ok" : "unavailable");
    } catch {
      setHealth("unavailable");
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => { void refreshHealth(); }, []);

  const update = <K extends keyof ProfileDraft>(key: K, value: ProfileDraft[K]) => {
    setSaved(false);
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const save = () => {
    setSaved(true);
  };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Saltar al contenido principal</a>
      <header className="topbar">
        <a className="brand" href="/" aria-label="JobScrapper, inicio"><span className="brand-mark" aria-hidden="true">J</span><span>JobScrapper</span></a>
        <div className="topbar-meta"><span className="environment-badge">Local</span><span className={`service-status ${health === "ok" ? "online" : ""}`}><span aria-hidden="true" />{health === "ok" ? "API conectada" : "API pendiente"}</span></div>
      </header>

      {/* Preserve the bootstrap contract: <main className="main-content" aria-labelledby="page-title"> */}
      <main className="main-content" aria-labelledby="page-title" id="main-content">
        <div className="page-heading"><div><p className="eyebrow">Configuración</p><h1 id="page-title">Tu perfil de búsqueda</h1><p className="hero-copy">Revisa lo que extrajimos de tu CV y ajusta qué hace relevante una oferta.</p></div><button type="button" className="secondary-button compact" onClick={refreshHealth} disabled={isRefreshing}>{isRefreshing ? "Comprobando…" : "Comprobar conexión"}</button></div>

        <nav className="tabs" role="tablist" aria-label="Secciones del perfil">
          <button id="tab-profile" role="tab" type="button" className={section === "profile" ? "tab active" : "tab"} aria-controls="profile-panel" aria-selected={section === "profile"} onClick={() => setSection("profile")}>CV y perfil</button>
          <button id="tab-preferences" role="tab" type="button" className={section === "preferences" ? "tab active" : "tab"} aria-controls="preferences-panel" aria-selected={section === "preferences"} onClick={() => setSection("preferences")}>Preferencias y pesos</button>
        </nav>

        {section === "profile" ? <ProfileSection draft={draft} cvName={cvName} setCvName={setCvName} update={update} /> : <PreferencesSection draft={draft} update={update} />}

        <div className="save-bar"><div aria-live="polite"><strong>{saved ? "Cambios guardados" : "Perfil versión 3"}</strong><span>{saved ? "Tu próxima evaluación usará esta configuración." : "Los cambios crearán una nueva versión y reevaluarán las ofertas."}</span></div><button type="button" className="primary-button" onClick={save}>{saved ? "Guardado" : "Guardar cambios"}</button></div>
      </main>
    </div>
  );
}

function ProfileSection({ draft, cvName, setCvName, update }: { draft: ProfileDraft; cvName: string; setCvName: (name: string) => void; update: <K extends keyof ProfileDraft>(key: K, value: ProfileDraft[K]) => void }) {
  return <div id="profile-panel" className="content-grid" role="tabpanel" aria-labelledby="tab-profile" tabIndex={0}>
    <section className="panel" aria-labelledby="cv-title"><div className="panel-heading"><div><p className="card-kicker">Extracción del CV</p><h2 id="cv-title">Revisa y corrige tu información</h2></div><span className="confidence-badge">92% de confianza</span></div><p className="muted">Edita cualquier campo antes de usarlo para encontrar ofertas.</p>
      <label className="upload-zone" htmlFor="cv-upload"><span className="upload-icon" aria-hidden="true">↑</span><span><strong>{cvName}</strong><small>PDF · actualizado hoy</small></span><span className="upload-action">Cambiar archivo</span><input id="cv-upload" name="cvFile" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => { const file = event.target.files?.[0]; if (file) setCvName(file.name); }} /></label>
      <div className="form-stack"><label>Nombre<input name="name" autoComplete="name" value={draft.name} onChange={(event) => update("name", event.target.value)} /></label><label>Titular profesional<input name="headline" autoComplete="organization-title" value={draft.headline} onChange={(event) => update("headline", event.target.value)} /></label><label>Habilidades clave<textarea name="skills" autoComplete="off" rows={3} value={draft.skills} onChange={(event) => update("skills", event.target.value)} /><small>Separa las habilidades con comas.</small></label><label>Experiencia profesional<textarea name="experience" autoComplete="off" rows={4} value={draft.experience} onChange={(event) => update("experience", event.target.value)} /></label><label>Idiomas y educación<textarea name="education" autoComplete="off" rows={2} value={`${draft.languages}\n${draft.education}`} onChange={(event) => { const [languages = "", education = ""] = event.target.value.split("\n"); update("languages", languages); update("education", education); }} /></label></div>
    </section>
    <aside className="panel summary-panel" aria-labelledby="summary-title"><p className="card-kicker">Resumen detectado</p><h2 id="summary-title">Así te estamos entendiendo</h2><div className="summary-item"><span className="summary-icon" aria-hidden="true">✦</span><div><strong>Perfil senior</strong><p>8 años de experiencia · Ingeniería</p></div></div><div className="summary-item"><span className="summary-icon" aria-hidden="true">◎</span><div><strong>5 habilidades principales</strong><p>Python · TypeScript · React · FastAPI · SQL</p></div></div><div className="summary-item"><span className="summary-icon" aria-hidden="true">↗</span><div><strong>Ubicación flexible</strong><p>CDMX, Guadalajara y remoto USA</p></div></div><div className="info-callout"><strong>¿Algo no coincide?</strong><p>La información editada aquí tiene prioridad sobre la extracción del documento.</p></div></aside>
  </div>;
}

function PreferencesSection({ draft, update }: { draft: ProfileDraft; update: <K extends keyof ProfileDraft>(key: K, value: ProfileDraft[K]) => void }) {
  const weightsTotal = draft.weightSkills + draft.weightExperience + draft.weightLocation + draft.weightMode;
  return <div id="preferences-panel" className="content-grid preferences-grid" role="tabpanel" aria-labelledby="tab-preferences" tabIndex={0}><section className="panel" aria-labelledby="preferences-title"><p className="card-kicker">Criterios de búsqueda</p><h2 id="preferences-title">Qué oportunidades quieres ver</h2><div className="form-grid"><label>Ubicaciones<input name="locations" autoComplete="address-level2" value={draft.locations} onChange={(event) => update("locations", event.target.value)} /><small>Usa comas para agregar varias.</small></label><label>Modalidad<select name="workMode" value={draft.mode} onChange={(event) => update("mode", event.target.value as WorkMode)}><option>Remoto</option><option>Híbrido</option><option>Presencial</option></select></label><label>Salario mínimo (MXN)<input name="minSalary" type="number" min="0" step="1000" value={draft.minSalary} onChange={(event) => update("minSalary", event.target.value)} /></label><label>Salario máximo (MXN)<input name="maxSalary" type="number" min="0" step="1000" value={draft.maxSalary} onChange={(event) => update("maxSalary", event.target.value)} /></label><label className="wide">Autorización de trabajo<textarea name="authorization" autoComplete="off" rows={2} value={draft.authorization} onChange={(event) => update("authorization", event.target.value)} /></label></div><fieldset className="constraints"><legend>Restricciones</legend><label className="checkbox-row"><input name="excludeNoSalary" type="checkbox" defaultChecked />Excluir ofertas sin rango salarial</label><label className="checkbox-row"><input name="excludeUnverified" type="checkbox" defaultChecked />Excluir empresas sin información verificable</label><label className="checkbox-row"><input name="allowRelocation" type="checkbox" />Mostrar ofertas que requieren reubicación</label></fieldset></section><section className="panel weights-panel" aria-labelledby="weights-title"><div className="panel-heading"><div><p className="card-kicker">Compatibilidad</p><h2 id="weights-title">Ajusta los pesos</h2></div><span className={`weight-total ${weightsTotal === 100 ? "valid" : "invalid"}`}>{weightsTotal}% total</span></div><p className="muted">Define qué factores influyen más en tu porcentaje de compatibilidad.</p><Weight label="Habilidades" name="weightSkills" value={draft.weightSkills} onChange={(value) => update("weightSkills", value)} /><Weight label="Experiencia" name="weightExperience" value={draft.weightExperience} onChange={(value) => update("weightExperience", value)} /><Weight label="Ubicación" name="weightLocation" value={draft.weightLocation} onChange={(value) => update("weightLocation", value)} /><Weight label="Modalidad" name="weightMode" value={draft.weightMode} onChange={(value) => update("weightMode", value)} /><div className="warning-callout" role="status"><strong>Reevaluación pendiente</strong><p>Al guardar, las ofertas existentes se volverán a evaluar con la versión 4 del perfil.</p></div></section></div>;
}

function Weight({ label, name, value, onChange }: { label: string; name: string; value: number; onChange: (value: number) => void }) {
  return <label className="weight-row"><span><strong>{label}</strong><output>{value}%</output></span><input name={name} aria-label={`Peso de ${label}`} autoComplete="off" type="range" min="0" max="100" step="5" value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}

export default App;
