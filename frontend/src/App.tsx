import { useEffect, useMemo, useState } from "react";
import { createApiClient, type HealthStatus } from "./api/client";
import "./styles.css";

type Section = "profile" | "preferences" | "vacancies";
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

type VacancyStatus = "new" | "changed" | "inactive" | "pending";
type Vacancy = { id: number; title: string; company: string; region: string; modality: WorkMode; score: number | null; source: string; publishedAt: string; status: VacancyStatus; description: string; salary: string; descriptionUrl: string; applicationUrl: string; gaps: string[]; recommendations: string[] };

const VACANCIES: Vacancy[] = [
  { id: 1, title: "Senior Backend Engineer", company: "Nubank", region: "CDMX", modality: "Híbrido", score: 94, source: "Greenhouse", publishedAt: "2026-07-19", status: "new", description: "Diseña servicios confiables y APIs que habilitan productos financieros para millones de personas.", salary: "$70,000–$90,000 MXN/mes", descriptionUrl: "https://boards.greenhouse.io/nubank/jobs/1", applicationUrl: "https://boards.greenhouse.io/nubank/jobs/1#apply", gaps: ["Experiencia con sistemas financieros regulados"], recommendations: ["Resalta tu experiencia diseñando APIs de alta disponibilidad", "Prepara ejemplos de observabilidad y respuesta a incidentes"] },
  { id: 2, title: "Staff Software Engineer", company: "Google", region: "USA", modality: "Remoto", score: 91, source: "Lever", publishedAt: "2026-07-18", status: "changed", description: "Lidera decisiones técnicas para plataformas distribuidas y equipos multifuncionales.", salary: "$180,000–$240,000 USD/año", descriptionUrl: "https://careers.google.com/jobs/results/2", applicationUrl: "https://careers.google.com/jobs/results/2#apply", gaps: ["Experiencia formal como staff engineer"], recommendations: ["Cuantifica el impacto técnico de tus proyectos", "Incluye liderazgo sin autoridad directa"] },
  { id: 3, title: "Full-stack Engineer", company: "Kueski", region: "Guadalajara", modality: "Híbrido", score: 86, source: "LinkedIn", publishedAt: "2026-07-16", status: "pending", description: "Construye experiencias de crédito digitales junto a producto, diseño y datos.", salary: "$55,000–$75,000 MXN/mes", descriptionUrl: "https://www.linkedin.com/jobs/view/3", applicationUrl: "https://www.linkedin.com/jobs/view/3", gaps: ["Experiencia reciente con React Native"], recommendations: ["Muestra colaboración con equipos de producto", "Agrega métricas de rendimiento frontend"] },
  { id: 4, title: "Platform Engineer", company: "Stripe", region: "USA", modality: "Remoto", score: 78, source: "Greenhouse", publishedAt: "2026-07-12", status: "inactive", description: "Mejora la plataforma de desarrollo y los sistemas de despliegue globales.", salary: "$160,000–$210,000 USD/año", descriptionUrl: "https://boards.greenhouse.io/stripe/jobs/4", applicationUrl: "https://boards.greenhouse.io/stripe/jobs/4#apply", gaps: ["Experiencia con Kubernetes a escala"], recommendations: ["Describe tus prácticas de infraestructura como código"] },
  { id: 5, title: "Software Engineering Manager", company: "Rappi", region: "CDMX", modality: "Presencial", score: 74, source: "Lever", publishedAt: "2026-07-10", status: "new", description: "Acompaña a un equipo de ingeniería y entrega productos de logística de alto impacto.", salary: "$80,000–$110,000 MXN/mes", descriptionUrl: "https://jobs.lever.co/rappi/5", applicationUrl: "https://jobs.lever.co/rappi/5/apply", gaps: ["Gestión de equipos mayores a 8 personas"], recommendations: ["Comparte cómo desarrollas talento y das feedback"] },
  { id: 6, title: "API Engineer", company: "Clip", region: "CDMX", modality: "Híbrido", score: 69, source: "LinkedIn", publishedAt: "2026-07-08", status: "pending", description: "Implementa APIs seguras para pagos y herramientas para comercios.", salary: "$50,000–$70,000 MXN/mes", descriptionUrl: "https://www.linkedin.com/jobs/view/6", applicationUrl: "https://www.linkedin.com/jobs/view/6", gaps: ["Conocimientos de PCI-DSS"], recommendations: ["Revisa patrones de idempotencia y seguridad de pagos"] },
];

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
          <button id="tab-vacancies" role="tab" type="button" className={section === "vacancies" ? "tab active" : "tab"} aria-controls="vacancies-panel" aria-selected={section === "vacancies"} onClick={() => setSection("vacancies")}>Ofertas</button>
          <button id="tab-profile" role="tab" type="button" className={section === "profile" ? "tab active" : "tab"} aria-controls="profile-panel" aria-selected={section === "profile"} onClick={() => setSection("profile")}>CV y perfil</button>
          <button id="tab-preferences" role="tab" type="button" className={section === "preferences" ? "tab active" : "tab"} aria-controls="preferences-panel" aria-selected={section === "preferences"} onClick={() => setSection("preferences")}>Preferencias y pesos</button>
        </nav>

        {section === "vacancies" ? <VacancyDashboard /> : section === "profile" ? <ProfileSection draft={draft} cvName={cvName} setCvName={setCvName} update={update} /> : <PreferencesSection draft={draft} update={update} />}

        {section !== "vacancies" && <div className="save-bar"><div aria-live="polite"><strong>{saved ? "Cambios guardados" : "Perfil versión 3"}</strong><span>{saved ? "Tu próxima evaluación usará esta configuración." : "Los cambios crearán una nueva versión y reevaluarán las ofertas."}</span></div><button type="button" className="primary-button" onClick={save}>{saved ? "Guardado" : "Guardar cambios"}</button></div>}
      </main>
    </div>
  );
}

function VacancyDashboard() {
  const [region, setRegion] = useState("Todas"); const [modality, setModality] = useState("Todas"); const [status, setStatus] = useState("Todos");
  const [company, setCompany] = useState(""); const [source, setSource] = useState("Todas"); const [minScore, setMinScore] = useState(0); const [date, setDate] = useState("Cualquier fecha");
  const [sort, setSort] = useState<"score" | "date" | "company">("score"); const [page, setPage] = useState(1); const pageSize = 4;
  const [selectedVacancy, setSelectedVacancy] = useState<Vacancy | null>(null);
  const filtered = useMemo(() => VACANCIES.filter((job) => (region === "Todas" || job.region === region) && (modality === "Todas" || job.modality === modality) && (status === "Todos" || job.status === status) && (source === "Todas" || job.source === source) && job.score !== null && job.score >= minScore && job.company.toLowerCase().includes(company.toLowerCase()) && (date === "Cualquier fecha" || job.publishedAt >= date)).sort((a, b) => sort === "score" ? (b.score ?? 0) - (a.score ?? 0) : sort === "company" ? a.company.localeCompare(b.company) : b.publishedAt.localeCompare(a.publishedAt)), [region, modality, status, source, minScore, company, date, sort]);
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize)); const visible = filtered.slice((page - 1) * pageSize, page * pageSize);
  useEffect(() => { setPage(1); }, [region, modality, status, source, minScore, company, date, sort]);
  if (selectedVacancy) return <VacancyDetail vacancy={selectedVacancy} onBack={() => setSelectedVacancy(null)} />;
  return <section id="vacancies-panel" className="vacancy-dashboard" role="tabpanel" aria-labelledby="tab-vacancies" tabIndex={0}>
    <div className="dashboard-heading"><div><p className="eyebrow">Búsqueda inteligente</p><h2>Ofertas para ti</h2><p className="hero-copy">{filtered.length} oportunidades compatibles, actualizadas continuamente.</p></div><button type="button" className="secondary-button">Actualizar ofertas</button></div>
    <div className="filter-panel" aria-label="Filtros de ofertas"><label>Región<select value={region} onChange={(e) => setRegion(e.target.value)}><option>Todas</option><option>CDMX</option><option>Guadalajara</option><option>USA</option></select></label><label>Modalidad<select value={modality} onChange={(e) => setModality(e.target.value)}><option>Todas</option><option>Remoto</option><option>Híbrido</option><option>Presencial</option></select></label><label>Score mínimo<output className="range-output">{minScore}%</output><input aria-label="Score mínimo" type="range" min="0" max="100" step="5" value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} /></label><label>Empresa<input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Buscar empresa" /></label><label>Fuente<select value={source} onChange={(e) => setSource(e.target.value)}><option>Todas</option><option>Greenhouse</option><option>Lever</option><option>LinkedIn</option></select></label><label>Desde<select value={date} onChange={(e) => setDate(e.target.value)}><option>Cualquier fecha</option><option>2026-07-15</option><option>2026-07-18</option></select></label><label>Estado<select value={status} onChange={(e) => setStatus(e.target.value)}><option>Todos</option><option value="new">Nuevas</option><option value="changed">Cambiaron</option><option value="inactive">Inactivas</option><option value="pending">Pendientes</option></select></label><label>Ordenar<select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}><option value="score">Compatibilidad</option><option value="date">Más recientes</option><option value="company">Empresa A-Z</option></select></label></div>
    <div className="status-legend" aria-label="Estados de ofertas">{([["new", "Nuevas"], ["changed", "Cambió contenido"], ["inactive", "Inactivas"], ["pending", "Pendientes"]] as const).map(([key, label]) => <span key={key}><i className={`status-dot ${key}`} aria-hidden="true" />{label}</span>)}</div>
    <div className="vacancy-list" aria-live="polite">{visible.length ? visible.map((job) => <article className="vacancy-card" key={job.id}><button type="button" className="vacancy-card-button" onClick={() => setSelectedVacancy(job)} aria-label={`Ver detalle de ${job.title} en ${job.company}`}><div className="vacancy-main"><div className="vacancy-title-row"><h3>{job.title}</h3><span className={`status-pill ${job.status}`}>{job.status === "new" ? "Nueva" : job.status === "changed" ? "Cambió" : job.status === "inactive" ? "Inactiva" : "Pendiente"}</span></div><p className="vacancy-company">{job.company} · {job.region} · {job.modality}</p><p className="vacancy-meta">Fuente: {job.source} · Publicada {job.publishedAt}</p></div><div className="score-badge" aria-label={`${job.score}% de compatibilidad`}><strong>{job.score}%</strong><span>match</span></div></button></article>) : <div className="empty-state"><strong>No hay ofertas con estos filtros.</strong><span>Prueba ampliar la región o bajar el score mínimo.</span></div>}</div>
    <div className="pagination" aria-label="Paginación"><span>Mostrando {visible.length ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, filtered.length)} de {filtered.length}</span><div><button type="button" className="secondary-button compact" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Anterior</button><span className="page-number">Página {page} de {pages}</span><button type="button" className="secondary-button compact" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Siguiente</button></div></div>
  </section>;
}

function VacancyDetail({ vacancy, onBack }: { vacancy: Vacancy; onBack: () => void }) {
  return <section className="vacancy-detail" aria-labelledby="vacancy-detail-title"><button type="button" className="secondary-button compact detail-back" onClick={onBack}>← Volver a ofertas</button><div className="detail-header"><div><p className="eyebrow">Detalle de oferta · {vacancy.source}</p><h2 id="vacancy-detail-title">{vacancy.title}</h2><p className="vacancy-company">{vacancy.company} · {vacancy.region}</p></div><div className="detail-score" aria-label={`${vacancy.score}% de compatibilidad`}><strong>{vacancy.score}%</strong><span>compatibilidad</span></div></div><div className="detail-grid"><div className="detail-main"><section className="panel" aria-labelledby="description-title"><h3 id="description-title">Descripción</h3><p>{vacancy.description}</p><dl className="detail-facts"><div><dt>Ubicación</dt><dd>{vacancy.region}</dd></div><div><dt>Modalidad</dt><dd>{vacancy.modality}</dd></div><div><dt>Salario estimado</dt><dd>{vacancy.salary}</dd></div><div><dt>Publicada</dt><dd>{vacancy.publishedAt}</dd></div></dl></section><section className="panel" aria-labelledby="recommendations-title"><h3 id="recommendations-title">Recomendaciones</h3><ul className="detail-list">{vacancy.recommendations.map((item) => <li key={item}>{item}</li>)}</ul></section></div><aside className="panel detail-aside" aria-labelledby="match-title"><h3 id="match-title">Compatibilidad</h3><p className="muted">Coincidencia calculada con tu perfil actual.</p><h4>Brechas detectadas</h4><ul className="detail-list">{vacancy.gaps.map((gap) => <li key={gap}>{gap}</li>)}</ul><div className="detail-actions"><a className="primary-button" href={vacancy.applicationUrl} target="_blank" rel="noopener noreferrer">Aplicar en {vacancy.company}<span aria-hidden="true"> ↗</span></a><a className="secondary-button" href={vacancy.descriptionUrl} target="_blank" rel="noopener noreferrer">Ver descripción original<span aria-hidden="true"> ↗</span></a></div></aside></div></section>;
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
