import { useCallback, useEffect, useState } from "react";
import { ApiRequestError, createApiClient, type ExecutionSummary, type HealthStatus, type JobDetailResponse, type JobSummary, type OperationsHealth, type OperationsMetrics, type SourceAdapterName, type SourceRunSummary, type SourceSummary } from "./api/client";
import "./styles.css";

type Section = "profile" | "preferences" | "vacancies" | "operations";
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

const MODALITY_MAP: Record<string, string> = { remote: "Remoto", hybrid: "Híbrido", onsite: "Presencial", unknown: "No especificada" };

function mapModality(m: string): string {
  return MODALITY_MAP[m.toLowerCase()] ?? m;
}

function mapStatus(s: string): "new" | "changed" | "inactive" | "pending" {
  if (s === "active") return "new";
  if (s === "inactive") return "inactive";
  return "pending";
}

function statusLabel(s: string): string {
  const labels: Record<string, string> = { new: "Nueva", changed: "Cambió", inactive: "Inactiva", pending: "Pendiente", active: "Activa" };
  return labels[s.toLowerCase()] ?? s;
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

const SOURCE_ADAPTERS: Array<{ value: SourceAdapterName; label: string; kind: "api" | "career_page"; fixtureLabel: string; fixtureHint: string }> = [
  { value: "json-api-feed", label: "JSON API o feed", kind: "api", fixtureLabel: "Payload JSON", fixtureHint: "Objeto con jobs o data no vacío; cada oferta requiere description_url o url." },
  { value: "greenhouse-career-page", label: "Greenhouse", kind: "career_page", fixtureLabel: "HTML de la página", fixtureHint: "HTML estático con tarjetas article/li y enlaces de oferta." },
  { value: "lever-career-page", label: "Lever", kind: "career_page", fixtureLabel: "HTML de la página", fixtureHint: "HTML estático con tarjetas article/li y enlaces de oferta." },
];

const TAB_SECTIONS: Section[] = ["vacancies", "profile", "preferences", "operations"];

function validateSourceFixture(adapter: SourceAdapterName, fixture: string): string | null {
  if (adapter === "json-api-feed") {
    let payload: unknown;
    try {
      payload = JSON.parse(fixture);
    } catch {
      return "El payload debe ser JSON válido.";
    }
    if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
      return "El payload debe ser un objeto JSON con jobs o data.";
    }
    const record = payload as Record<string, unknown>;
    const jobs = Array.isArray(record.jobs) ? record.jobs : undefined;
    const data = Array.isArray(record.data) ? record.data : undefined;
    const items = jobs ?? data;
    if (!items || items.length === 0) {
      return "El payload debe incluir una lista jobs o data con al menos una oferta.";
    }
    const invalidIndex = items.findIndex((item) => {
      if (typeof item !== "object" || item === null || Array.isArray(item)) return true;
      const job = item as Record<string, unknown>;
      const url = job.description_url ?? job.url;
      return typeof url !== "string" || url.trim().length === 0;
    });
    if (invalidIndex >= 0) {
      return `La oferta ${invalidIndex + 1} debe incluir description_url o url.`;
    }
    return null;
  }

  const cardPattern = /<(article|li)\b[^>]*>[\s\S]*?<a\b[^>]*href\s*=\s*["'][^"']+["'][^>]*>[\s\S]*?<\/\1>/i;
  if (!cardPattern.test(fixture)) {
    return "El HTML debe incluir al menos una tarjeta article/li con un enlace de oferta.";
  }
  return null;
}

function App() {
  const [section, setSection] = useState<Section>("profile");
  const [draft, setDraft] = useState<ProfileDraft>(initialDraft);
  const [health, setHealth] = useState<HealthStatus>("unavailable");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [cvName, setCvName] = useState("CV_Carlos_Castaneda.pdf");
  const [profileId, setProfileId] = useState<number | null>(null);
  const [profileVersion, setProfileVersion] = useState(1);
  const [profileError, setProfileError] = useState<string | null>(null);

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

  useEffect(() => {
    const stored = localStorage.getItem("profileId");
    if (stored) {
      const id = parseInt(stored);
      if (!isNaN(id)) {
        apiClient.getProfile(id).then((p) => {
          setProfileId(p.id);
          setProfileVersion(p.version);
          setCvName(p.cv_filename || cvName);
          const toStrings = (arr: unknown[]) => arr.map((item) => (typeof item === "object" && item !== null ? String((item as Record<string, unknown>).text ?? "") : String(item)));
          setDraft({
            name: p.name,
            headline: p.seniority || initialDraft.headline,
            skills: Array.isArray(p.skills) ? toStrings(p.skills).join(", ") : initialDraft.skills,
            experience: Array.isArray(p.experience) ? toStrings(p.experience).join("\n") : initialDraft.experience,
            languages: Array.isArray(p.languages) ? toStrings(p.languages).join("\n") : initialDraft.languages,
            education: Array.isArray(p.education) ? toStrings(p.education).join("\n") : initialDraft.education,
            locations: p.preferences?.locations?.join(", ") || initialDraft.locations,
            mode: (p.preferences?.modalities?.[0] === "remote" ? "Remoto" : p.preferences?.modalities?.[0] === "hybrid" ? "Híbrido" : p.preferences?.modalities?.[0] === "onsite" ? "Presencial" : initialDraft.mode) as WorkMode,
            authorization: p.preferences?.work_authorization?.join(", ") || initialDraft.authorization,
            minSalary: p.preferences?.salary_min?.toString() || initialDraft.minSalary,
            maxSalary: p.preferences?.salary_max?.toString() || initialDraft.maxSalary,
            weightSkills: (p.preferences?.weights as Record<string, number>)?.skills ?? initialDraft.weightSkills,
            weightExperience: (p.preferences?.weights as Record<string, number>)?.experience ?? initialDraft.weightExperience,
            weightLocation: (p.preferences?.weights as Record<string, number>)?.location ?? initialDraft.weightLocation,
            weightMode: (p.preferences?.weights as Record<string, number>)?.modality ?? initialDraft.weightMode,
          });
        }).catch(() => localStorage.removeItem("profileId"));
      }
    }
  }, []);

  const update = <K extends keyof ProfileDraft>(key: K, value: ProfileDraft[K]) => {
    setSaved(false);
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const handleTabKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    const currentIndex = TAB_SECTIONS.indexOf(section);
    let nextIndex = currentIndex;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") nextIndex = (currentIndex + 1) % TAB_SECTIONS.length;
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") nextIndex = (currentIndex - 1 + TAB_SECTIONS.length) % TAB_SECTIONS.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = TAB_SECTIONS.length - 1;
    if (nextIndex !== currentIndex) {
      event.preventDefault();
      setSection(TAB_SECTIONS[nextIndex]);
      document.getElementById(`tab-${TAB_SECTIONS[nextIndex]}`)?.focus();
    }
  };

  const handleCvUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setCvName(file.name);
    try {
      const result = await apiClient.uploadProfile(file);
      setProfileId(result.id);
      setProfileVersion(result.version);
      localStorage.setItem("profileId", result.id.toString());
      const toStrings = (arr: unknown[]) => arr.map((item) => (typeof item === "object" && item !== null ? String((item as Record<string, unknown>).text ?? "") : String(item)));
      setDraft((current) => ({
        ...current,
        name: result.name,
        skills: Array.isArray(result.skills) ? toStrings(result.skills).join(", ") : current.skills,
        experience: Array.isArray(result.experience) ? toStrings(result.experience).join("\n") : current.experience,
        languages: Array.isArray(result.languages) ? toStrings(result.languages).join("\n") : current.languages,
        education: Array.isArray(result.education) ? toStrings(result.education).join("\n") : current.education,
      }));
      setProfileError(null);
    } catch { setProfileError("No se pudo subir el CV."); }
  };

  const save = async () => {
    if (!profileId) { setProfileError("Sube un CV antes de guardar."); return; }
    setSaving(true); setProfileError(null);
    try {
      if (section === "profile") {
        const updated = await apiClient.updateProfile(profileId, {
          name: draft.name,
          skills: draft.skills.split(",").map((s) => s.trim()).filter(Boolean),
          experience: [draft.experience],
          languages: draft.languages.split("\n").map((s) => s.trim()).filter(Boolean),
          education: [draft.education],
        });
        setProfileVersion(updated.version);
      } else {
        await apiClient.updateProfilePreferences(profileId, {
          locations: draft.locations.split(",").map((s) => s.trim()).filter(Boolean),
          modalities: [draft.mode === "Remoto" ? "remote" : draft.mode === "Híbrido" ? "hybrid" : "onsite"],
          salary_min: parseInt(draft.minSalary) || undefined,
          salary_max: parseInt(draft.maxSalary) || undefined,
          work_authorization: draft.authorization ? [draft.authorization] : undefined,
          weights: { skills: draft.weightSkills, experience: draft.weightExperience, location: draft.weightLocation, modality: draft.weightMode },
        });
      }
      setSaved(true);
    } catch { setProfileError("No se pudieron guardar los cambios."); }
    finally { setSaving(false); }
  };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Saltar al contenido principal</a>
      <header className="topbar">
        <a className="brand" href="/" aria-label="JobScrapper, inicio"><span className="brand-mark" aria-hidden="true">J</span><span>JobScrapper</span></a>
        <div className="topbar-meta"><span className="environment-badge">Local</span><span className={`service-status ${health === "ok" ? "online" : ""}`}><span aria-hidden="true" />{health === "ok" ? "API conectada" : "API pendiente"}</span></div>
      </header>

      <main className="main-content" aria-labelledby="page-title" id="main-content">
        <div className="page-heading"><div><p className="eyebrow">Configuración</p><h1 id="page-title">Tu perfil de búsqueda</h1><p className="hero-copy">Revisa lo que extrajimos de tu CV y ajusta qué hace relevante una oferta.</p></div><button type="button" className="secondary-button compact" onClick={refreshHealth} disabled={isRefreshing}>{isRefreshing ? "Comprobando…" : "Comprobar conexión"}</button></div>

        <nav className="tabs" role="tablist" aria-label="Secciones del perfil">
          <button id="tab-vacancies" role="tab" type="button" className={section === "vacancies" ? "tab active" : "tab"} aria-controls="vacancies-panel" aria-selected={section === "vacancies"} tabIndex={section === "vacancies" ? 0 : -1} onKeyDown={handleTabKeyDown} onClick={() => setSection("vacancies")}>Ofertas</button>
          <button id="tab-profile" role="tab" type="button" className={section === "profile" ? "tab active" : "tab"} aria-controls="profile-panel" aria-selected={section === "profile"} tabIndex={section === "profile" ? 0 : -1} onKeyDown={handleTabKeyDown} onClick={() => setSection("profile")}>CV y perfil</button>
          <button id="tab-preferences" role="tab" type="button" className={section === "preferences" ? "tab active" : "tab"} aria-controls="preferences-panel" aria-selected={section === "preferences"} tabIndex={section === "preferences" ? 0 : -1} onKeyDown={handleTabKeyDown} onClick={() => setSection("preferences")}>Preferencias y pesos</button>
          <button id="tab-operations" role="tab" type="button" className={section === "operations" ? "tab active" : "tab"} aria-controls="operations-panel" aria-selected={section === "operations"} tabIndex={section === "operations" ? 0 : -1} onKeyDown={handleTabKeyDown} onClick={() => setSection("operations")}>Operación</button>
        </nav>

        {profileError && <div className="error-callout" role="alert"><strong>Error</strong><span>{profileError}</span></div>}

        {section === "vacancies" ? <VacancyDashboard /> : section === "operations" ? <OperationsDashboard /> : section === "profile" ? <ProfileSection draft={draft} cvName={cvName} onUpload={handleCvUpload} update={update} /> : <PreferencesSection draft={draft} update={update} />}

        {(section === "profile" || section === "preferences") && <div className="save-bar"><div aria-live="polite"><strong>{saved ? "Cambios guardados" : `Perfil versión ${profileVersion}`}</strong><span>{profileId ? (saved ? "Tu próxima evaluación usará esta configuración." : "Los cambios crearán una nueva versión y reevaluarán las ofertas.") : "Sube un CV para comenzar."}</span></div><button type="button" className="primary-button" onClick={save} disabled={saving}>{saving ? "Guardando…" : saved ? "Guardado" : "Guardar cambios"}</button></div>}
      </main>
    </div>
  );
}

function OperationsDashboard() {
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [executions, setExecutions] = useState<ExecutionSummary[]>([]);
  const [metrics, setMetrics] = useState<OperationsMetrics | null>(null);
  const [operationsHealth, setOperationsHealth] = useState<OperationsHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formAdapter, setFormAdapter] = useState<SourceAdapterName>("json-api-feed");
  const [formUrl, setFormUrl] = useState("");
  const [formTermsUrl, setFormTermsUrl] = useState("");
  const [formMode, setFormMode] = useState<"fixture" | "network">("fixture");
  const [formFixture, setFormFixture] = useState("");
  const [formTermsAccepted, setFormTermsAccepted] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formErrorFields, setFormErrorFields] = useState<Array<{ field?: string; message?: string }>>([]);

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const [nextSources, nextExecutions, nextMetrics, nextHealth] = await Promise.all([apiClient.getSources(), apiClient.getExecutions(), apiClient.getMetrics(), apiClient.getOperationsHealth()]);
      setSources(nextSources); setExecutions(nextExecutions); setMetrics(nextMetrics); setOperationsHealth(nextHealth); setLastUpdated(new Date().toISOString());
    } catch { setError("No pudimos consultar la API."); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);

  const manualRefresh = async () => {
    setRefreshing(true); setError(null);
    try { const run = await apiClient.refresh(); setExecutions((current) => [run, ...current].slice(0, 10)); setLastUpdated(new Date().toISOString()); }
    catch { setError("La actualización no pudo iniciarse. Revisa si ya existe una ejecución en curso."); }
    finally { setRefreshing(false); }
  };

  const toggleSource = async (id: number, current: boolean) => {
    try { await apiClient.updateSource(id, { enabled: !current }); void load(); }
    catch { setError("No se pudo cambiar el estado de la fuente."); }
  };

  const createSource = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormErrorFields([]);
    const adapter = SOURCE_ADAPTERS.find((item) => item.value === formAdapter) ?? SOURCE_ADAPTERS[0];
    const name = formName.trim();
    const url = formUrl.trim();
    const termsUrl = formTermsUrl.trim();
    const fixture = formFixture.trim();
    if (!name) { setFormError("Indica un nombre para la fuente."); return; }
    if (!formTermsAccepted) { setFormError("Debes aceptar los términos de uso de la fuente antes de activarla."); return; }
    if (formMode === "network" && !url) { setFormError("La URL base es obligatoria en modo red."); return; }
    if (formMode === "fixture" && !fixture) { setFormError(`Agrega ${adapter.fixtureLabel.toLowerCase()} o cambia a modo red.`); return; }
    if (formMode === "fixture") {
      const fixtureError = validateSourceFixture(adapter.value, fixture);
      if (fixtureError) { setFormError(fixtureError); return; }
    }
    try {
      const config = {
        adapter: adapter.value,
        allow_network: formMode === "network",
        terms_accepted: true,
        ...(formMode === "fixture" ? (adapter.value === "json-api-feed" ? { payload: fixture } : { html: fixture }) : {}),
      };
      await apiClient.createSource({ name, kind: adapter.kind, base_url: url || undefined, terms_url: termsUrl || undefined, terms_accepted: true, config });
      setShowForm(false); setFormName(""); setFormAdapter("json-api-feed"); setFormUrl(""); setFormTermsUrl(""); setFormMode("fixture"); setFormFixture(""); setFormTermsAccepted(false); setFormErrorFields([]);
      void load();
    } catch (caught) {
      setFormError(caught instanceof ApiRequestError ? caught.message : "No se pudo crear la fuente.");
      setFormErrorFields(caught instanceof ApiRequestError ? caught.fields : []);
    }
  };

  const deleteSource = async (id: number, name: string) => {
    if (!confirm(`¿Eliminar la fuente "${name}"?`)) return;
    try { await apiClient.deleteSource(id); void load(); }
    catch { setError("No se pudo eliminar la fuente."); }
  };

  const healthy = operationsHealth?.status === "ok";
  const totalJobs = metrics?.jobs.active ?? 0;
  const totalJobsRegistered = metrics?.jobs.total ?? 0;
  const totalExecutions = metrics?.executions.total ?? 0;
  const runningExecutions = metrics?.executions.running ?? 0;
  const latestSourceRuns = new Map<number, SourceRunSummary>();
  executions.forEach((execution) => {
    execution.source_runs?.forEach((run) => {
      if (!latestSourceRuns.has(run.source_id)) latestSourceRuns.set(run.source_id, run);
    });
  });
  const selectedAdapter = SOURCE_ADAPTERS.find((item) => item.value === formAdapter) ?? SOURCE_ADAPTERS[0];

  return <section id="operations-panel" className="operations-dashboard" role="tabpanel" aria-labelledby="tab-operations" tabIndex={0}>
    <div className="dashboard-heading"><div><p className="eyebrow">Centro de operaciones</p><h2>Estado de la búsqueda</h2><p className="hero-copy">Supervisa fuentes, ejecuciones y la salud de tus integraciones locales.</p></div><button type="button" className="primary-button" onClick={manualRefresh} disabled={refreshing} aria-busy={refreshing}>{refreshing ? "Actualizando…" : "Actualizar ofertas"}</button></div>
    {error && <div className="error-callout" role="alert"><strong>Error</strong><span>{error}</span><button type="button" className="secondary-button compact" onClick={() => void load()}>Reintentar</button></div>}
    {loading ? <div className="loading-state" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" />Cargando estado operativo…</div> : <>
      <div className="ops-metrics" aria-label="Métricas de operación"><Metric label="Ofertas activas" value={totalJobs} hint={`${totalJobsRegistered} registradas`} /><Metric label="Ejecuciones" value={totalExecutions} hint={`${runningExecutions} en curso`} /><Metric label="Fuentes activas" value={sources.filter((s) => s.enabled).length} hint={`${sources.length} configuradas`} /><Metric label="Última actualización" value={lastUpdated ? new Date(lastUpdated).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" }) : "—"} hint="hora local" /></div>
      <div className="operations-grid">
        <section className="panel" aria-labelledby="sources-title">
          <div className="panel-heading"><div><p className="card-kicker">Ingesta</p><h3 id="sources-title">Fuentes conectadas</h3></div><span className="source-count">{sources.filter((s) => s.enabled).length}/{sources.length} activas</span></div>
          <p className="muted">Activa o pausa una fuente sin perder su configuración.</p>
          {sources.length ? <ul className="source-list">{sources.map((source) => {
            const run = latestSourceRuns.get(source.id);
            const runClass = run?.status === "success" ? "healthy" : run ? "failed" : "unknown";
            return <li key={source.id}>
              <div className="source-details"><strong>{source.name}</strong><span>{source.config?.adapter ?? source.kind} · {source.base_url || "Fixture local"}</span><span className={`source-run-status ${runClass}`} aria-label={run ? `Última ejecución: ${run.status}` : "Sin ejecuciones"}>{run ? `${run.status} · ${run.jobs_found} ofertas` : "Sin ejecuciones"}</span>{run?.error && <span className="source-error" title={run.error}>{run.error}</span>}</div>
              <div className="source-actions"><button type="button" className={`toggle ${source.enabled ? "on" : ""}`} aria-pressed={source.enabled} onClick={() => toggleSource(source.id, source.enabled)}><span aria-hidden="true" />{source.enabled ? "Activa" : "Pausada"}</button><button type="button" className="toggle danger" onClick={() => deleteSource(source.id, source.name)}>Eliminar</button></div>
            </li>;
          })}</ul> : <div className="empty-state"><strong>No hay fuentes configuradas.</strong><span>Agrega una fuente para iniciar la búsqueda.</span></div>}
          <button type="button" className="secondary-button compact" style={{ marginTop: "0.75rem" }} onClick={() => setShowForm(!showForm)}>{showForm ? "Cancelar" : "Agregar fuente"}</button>
          {showForm && <form onSubmit={createSource} className="source-form">
            <p className="source-form-intro">Configura una fuente completa para que la próxima actualización pueda ejecutarla.</p>
            {formError && <div className="error-callout" role="alert"><strong>No se creó</strong><span>{formError}</span>{formErrorFields.length > 0 && <ul className="form-error-list">{formErrorFields.map((field, index) => <li key={`${field.field ?? "error"}-${index}`}><strong>{field.field ?? "Revisa este campo"}:</strong> {field.message ?? "Corrige este valor y vuelve a intentar."}</li>)}</ul>}</div>}
            <label htmlFor="source-name">Nombre<input id="source-name" name="sourceName" autoComplete="organization" value={formName} onChange={(e) => setFormName(e.target.value)} required placeholder="Ej: Greenhouse Acme" /></label>
            <label htmlFor="source-adapter">Adaptador<select id="source-adapter" name="sourceAdapter" autoComplete="off" value={formAdapter} onChange={(e) => setFormAdapter(e.target.value as SourceAdapterName)} aria-describedby="adapter-hint">{SOURCE_ADAPTERS.map((adapter) => <option key={adapter.value} value={adapter.value}>{adapter.label}</option>)}</select><small id="adapter-hint">El adaptador determina el formato que se leerá.</small></label>
            <label htmlFor="source-mode">Modo de ingesta<select id="source-mode" name="sourceMode" autoComplete="off" value={formMode} onChange={(e) => setFormMode(e.target.value as "fixture" | "network")}><option value="fixture">Fixture local (recomendado para probar)</option><option value="network">Red (consulta la URL)</option></select></label>
            <label htmlFor="source-base-url">URL base{formMode === "network" ? <input id="source-base-url" name="baseUrl" autoComplete="url" value={formUrl} onChange={(e) => setFormUrl(e.target.value)} required placeholder="https://ejemplo.com/jobs" type="url" /> : <input id="source-base-url" name="baseUrl" autoComplete="url" value={formUrl} onChange={(e) => setFormUrl(e.target.value)} placeholder="Opcional: se usa para resolver enlaces relativos" type="url" />}<small>{formMode === "network" ? "Debe ser una URL http(s) accesible y permitida por robots.txt." : "Opcional en modo fixture."}</small></label>
            <label htmlFor="source-terms-url">URL de términos de uso<input id="source-terms-url" name="termsUrl" autoComplete="url" value={formTermsUrl} onChange={(e) => setFormTermsUrl(e.target.value)} placeholder="https://ejemplo.com/terms" type="url" /><small>Guarda la referencia que revisaste antes de habilitar la fuente.</small></label>
            <label htmlFor="source-fixture">{selectedAdapter.fixtureLabel}{formMode === "fixture" && <textarea id="source-fixture" name="fixture" autoComplete="off" value={formFixture} onChange={(e) => setFormFixture(e.target.value)} required rows={selectedAdapter.value === "json-api-feed" ? 6 : 5} placeholder={selectedAdapter.value === "json-api-feed" ? '{"jobs": [{"title": "...", "description_url": "https://..."}]}' : "<article data-job=\"true\">...</article>"} />}<small>{formMode === "fixture" ? selectedAdapter.fixtureHint : "No se necesita fixture en modo red."}</small></label>
            <label className="checkbox-row source-terms" htmlFor="source-terms-accepted"><input type="checkbox" checked={formTermsAccepted} onChange={(e) => setFormTermsAccepted(e.target.checked)} required id="source-terms-accepted" name="termsAccepted" autoComplete="off" />Confirmo que revisé y acepto los términos de uso de esta fuente.</label>
            <button type="submit" className="primary-button">Crear fuente ejecutable</button>
          </form>}
        </section>
        <section className="panel" aria-labelledby="health-title"><div className="panel-heading"><div><p className="card-kicker">Disponibilidad</p><h3 id="health-title">Salud de servicios</h3></div><span className={`health-badge ${healthy ? "healthy" : "degraded"}`}><i aria-hidden="true" />{healthy ? "Saludable" : "Revisar"}</span></div><ul className="health-list">{Object.entries(operationsHealth?.checks ?? { api: { status: "local" }, database: { status: "local" }, ollama: { status: "opcional" }, notion: { status: "opcional" } }).map(([name, check]) => <li key={name}><span>{name === "api" ? "API" : name === "database" ? "SQLite" : name === "ollama" ? "Modelo local" : "Notion"}</span><strong className={check.status === "ok" || check.status === "local" ? "ok" : "muted-status"}>{check.status}</strong></li>)}</ul></section>
      </div>
      <section className="panel execution-panel" aria-labelledby="executions-title"><div className="panel-heading"><div><p className="card-kicker">Historial</p><h3 id="executions-title">Últimas ejecuciones</h3></div><span className="muted">{executions.length} mostradas</span></div>{executions.length ? <div className="execution-table-wrap"><table><caption className="sr-only">Historial de ejecuciones de búsqueda</caption><thead><tr><th scope="col">Estado</th><th scope="col">Inicio</th><th scope="col">Ofertas</th><th scope="col">Errores</th></tr></thead><tbody>{executions.map((run) => <tr key={run.run_id}><td><span className={`run-status ${run.status}`}>{run.status}</span></td><td>{run.started_at ? new Date(run.started_at).toLocaleString("es-MX") : "—"}</td><td>{run.metrics.jobs_found ?? 0}</td><td>{run.metrics.sources_failed ?? (run.error ? 1 : 0)}</td></tr>)}</tbody></table></div> : <div className="empty-state"><strong>Aún no hay ejecuciones.</strong><span>Usa “Actualizar ofertas” para iniciar la primera.</span></div>}</section>
    </>}
  </section>;
}

function Metric({ label, value, hint, accent = false }: { label: string; value: number | string; hint: string; accent?: boolean }) { return <div className={`metric-card ${accent ? "accent" : ""}`}><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>; }

function VacancyDashboard() {
  const [region, setRegion] = useState("Todas");
  const [modality, setModality] = useState("Todas");
  const [status, setStatus] = useState("Todos");
  const [company, setCompany] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [sort, setSort] = useState<"score" | "date" | "company">("score");
  const [page, setPage] = useState(1);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);

  const pageSize = 4;

  const fetchJobs = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const orderMap: Record<string, string> = { score: "score", date: "detected_at", company: "company" };
      const result = await apiClient.listJobs({
        page, page_size: pageSize,
        region: region === "Todas" ? undefined : region.toLowerCase(),
        modality: modality === "Todas" ? undefined : modality.toLowerCase(),
        status: status === "Todos" ? undefined : status === "new" ? "active" : status.toLowerCase(),
        company: company || undefined,
        min_score: minScore || undefined,
        order: orderMap[sort],
        direction: "desc",
      });
      setJobs(result.items); setTotal(result.total); setTotalPages(result.total_pages);
    } catch { setError("No pudimos cargar las ofertas."); }
    finally { setLoading(false); }
  }, [region, modality, status, company, minScore, sort, page]);

  useEffect(() => { void fetchJobs(); }, [fetchJobs]);
  useEffect(() => { setPage(1); }, [region, modality, status, company, minScore, sort]);

  if (selectedJobId) return <VacancyDetail jobId={selectedJobId} onBack={() => setSelectedJobId(null)} />;

  return <section id="vacancies-panel" className="vacancy-dashboard" role="tabpanel" aria-labelledby="tab-vacancies" tabIndex={0}>
    <div className="dashboard-heading"><div><p className="eyebrow">Búsqueda inteligente</p><h2>Ofertas para ti</h2><p className="hero-copy">{total} oportunidades compatibles, actualizadas continuamente.</p></div><button type="button" className="secondary-button" onClick={() => void fetchJobs()}>Actualizar ofertas</button></div>
    <div className="filter-panel" aria-label="Filtros de ofertas"><label>Región<select value={region} onChange={(e) => setRegion(e.target.value)}><option>Todas</option><option>CDMX</option><option>Guadalajara</option><option>USA</option><option>Mexico</option><option>Other</option></select></label><label>Modalidad<select value={modality} onChange={(e) => setModality(e.target.value)}><option>Todas</option><option>Remoto</option><option>Híbrido</option><option>Presencial</option></select></label><label>Score mínimo<output className="range-output">{minScore}%</output><input aria-label="Score mínimo" type="range" min="0" max="100" step="5" value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} /></label><label>Empresa<input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Buscar empresa" /></label><label>Estado<select value={status} onChange={(e) => setStatus(e.target.value)}><option>Todos</option><option value="new">Nuevas</option><option value="inactive">Inactivas</option></select></label><label>Ordenar<select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}><option value="score">Compatibilidad</option><option value="date">Más recientes</option><option value="company">Empresa A-Z</option></select></label></div>
    <div className="status-legend" aria-label="Estados de ofertas">{([["new", "Nuevas"], ["inactive", "Inactivas"], ["active", "Activas"]] as const).map(([key, label]) => <span key={key}><i className={`status-dot ${key}`} aria-hidden="true" />{label}</span>)}</div>
    {error && <div className="error-callout" role="alert"><strong>Error</strong><span>{error}</span><button type="button" className="secondary-button compact" onClick={() => void fetchJobs()}>Reintentar</button></div>}
    {loading ? <div className="loading-state" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" />Cargando ofertas…</div> : <div className="vacancy-list" aria-live="polite">{jobs.length ? jobs.map((job) => <article className="vacancy-card" key={job.id}><button type="button" className="vacancy-card-button" onClick={() => setSelectedJobId(job.id)} aria-label={`Ver detalle de ${job.title} en ${job.company}`}><div className="vacancy-main"><div className="vacancy-title-row"><h3>{job.title}</h3><span className={`status-pill ${mapStatus(job.status)}`}>{statusLabel(job.status)}</span></div><p className="vacancy-company">{job.company} · {job.region} · {mapModality(job.modality)}</p><p className="vacancy-meta">{job.published_at ? `Publicada ${job.published_at}` : ""}</p></div><div className="score-badge" aria-label={`${job.score ?? "N/A"}% de compatibilidad`}><strong>{job.score != null ? `${job.score}%` : "—"}</strong><span>match</span></div></button></article>) : <div className="empty-state"><strong>No hay ofertas con estos filtros.</strong><span>Prueba ampliar la región o bajar el score mínimo.</span></div>}</div>}
    <div className="pagination" aria-label="Paginación"><span>Mostrando {jobs.length ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, total)} de {total}</span><div><button type="button" className="secondary-button compact" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button><span className="page-number">Página {page} de {Math.max(1, totalPages)}</span><button type="button" className="secondary-button compact" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Siguiente</button></div></div>
  </section>;
}

function VacancyDetail({ jobId, onBack }: { jobId: number; onBack: () => void }) {
  const [detail, setDetail] = useState<JobDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { apiClient.getJobDetail(jobId).then(setDetail).finally(() => setLoading(false)); }, [jobId]);

  if (loading) return <section className="vacancy-detail" aria-labelledby="vacancy-detail-title"><button type="button" className="secondary-button compact detail-back" onClick={onBack}>← Volver a ofertas</button><div className="loading-state" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" />Cargando detalle…</div></section>;
  if (!detail) return <section className="vacancy-detail" aria-labelledby="vacancy-detail-title"><button type="button" className="secondary-button compact detail-back" onClick={onBack}>← Volver a ofertas</button><div className="error-callout" role="alert">No se pudo cargar el detalle.</div></section>;

  const salary = detail.salary_min != null && detail.salary_max != null ? `$${detail.salary_min?.toLocaleString()}–$${detail.salary_max?.toLocaleString()} ${detail.salary_currency ?? ""}/año` : "No especificado";
  const gaps = (detail.evaluation?.gaps ?? []) as string[];
  const recommendations = (detail.recommendations ?? []) as string[];

  return <section className="vacancy-detail" aria-labelledby="vacancy-detail-title"><button type="button" className="secondary-button compact detail-back" onClick={onBack}>← Volver a ofertas</button><div className="detail-header"><div><p className="eyebrow">Detalle de oferta</p><h2 id="vacancy-detail-title">{detail.title}</h2><p className="vacancy-company">{detail.company} · {detail.region}</p></div><div className="detail-score" aria-label={`${detail.score ?? "N/A"}% de compatibilidad`}><strong>{detail.score != null ? `${detail.score}%` : "—"}</strong><span>compatibilidad</span></div></div><div className="detail-grid"><div className="detail-main"><section className="panel" aria-labelledby="description-title"><h3 id="description-title">Descripción</h3><p>{detail.description}</p><dl className="detail-facts"><div><dt>Ubicación</dt><dd>{detail.region}</dd></div><div><dt>Modalidad</dt><dd>{mapModality(detail.modality)}</dd></div><div><dt>Salario estimado</dt><dd>{salary}</dd></div><div><dt>Publicada</dt><dd>{detail.published_at ?? "—"}</dd></div></dl></section>{recommendations.length > 0 && <section className="panel" aria-labelledby="recommendations-title"><h3 id="recommendations-title">Recomendaciones</h3><ul className="detail-list">{recommendations.map((item, i) => <li key={i}>{item}</li>)}</ul></section>}</div><aside className="panel detail-aside" aria-labelledby="match-title"><h3 id="match-title">Compatibilidad</h3><p className="muted">Coincidencia calculada con tu perfil actual.</p>{gaps.length > 0 && <><h4>Brechas detectadas</h4><ul className="detail-list">{gaps.map((gap, i) => <li key={i}>{gap}</li>)}</ul></>}<div className="detail-actions"><a className="primary-button" href={detail.application_url ?? detail.description_url} target="_blank" rel="noopener noreferrer">Aplicar<span aria-hidden="true"> ↗</span></a><a className="secondary-button" href={detail.description_url} target="_blank" rel="noopener noreferrer">Ver descripción original<span aria-hidden="true"> ↗</span></a></div></aside></div></section>;
}

function ProfileSection({ draft, cvName, onUpload, update }: { draft: ProfileDraft; cvName: string; onUpload: (event: React.ChangeEvent<HTMLInputElement>) => void; update: <K extends keyof ProfileDraft>(key: K, value: ProfileDraft[K]) => void }) {
  return <div id="profile-panel" className="content-grid" role="tabpanel" aria-labelledby="tab-profile" tabIndex={0}>
    <section className="panel" aria-labelledby="cv-title"><div className="panel-heading"><div><p className="card-kicker">Extracción del CV</p><h2 id="cv-title">Revisa y corrige tu información</h2></div><span className="confidence-badge">92% de confianza</span></div><p className="muted">Edita cualquier campo antes de usarlo para encontrar ofertas.</p>
      <label className="upload-zone" htmlFor="cv-upload"><span className="upload-icon" aria-hidden="true">↑</span><span><strong>{cvName}</strong><small>PDF · DOCX</small></span><span className="upload-action">Cambiar archivo</span><input id="cv-upload" name="cvFile" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={onUpload} /></label>
      <div className="form-stack"><label>Nombre<input name="name" autoComplete="name" value={draft.name} onChange={(event) => update("name", event.target.value)} /></label><label>Titular profesional<input name="headline" autoComplete="organization-title" value={draft.headline} onChange={(event) => update("headline", event.target.value)} /></label><label>Habilidades clave<textarea name="skills" autoComplete="off" rows={3} value={draft.skills} onChange={(event) => update("skills", event.target.value)} /><small>Separa las habilidades con comas.</small></label><label>Experiencia profesional<textarea name="experience" autoComplete="off" rows={4} value={draft.experience} onChange={(event) => update("experience", event.target.value)} /></label><label>Idiomas y educación<textarea name="education" autoComplete="off" rows={2} value={`${draft.languages}\n${draft.education}`} onChange={(event) => { const [languages = "", education = ""] = event.target.value.split("\n"); update("languages", languages); update("education", education); }} /></label></div>
    </section>
    <aside className="panel summary-panel" aria-labelledby="summary-title"><p className="card-kicker">Resumen detectado</p><h2 id="summary-title">Así te estamos entendiendo</h2><div className="summary-item"><span className="summary-icon" aria-hidden="true">✦</span><div><strong>Perfil senior</strong><p>8 años de experiencia · Ingeniería</p></div></div><div className="summary-item"><span className="summary-icon" aria-hidden="true">◎</span><div><strong>5 habilidades principales</strong><p>Python · TypeScript · React · FastAPI · SQL</p></div></div><div className="summary-item"><span className="summary-icon" aria-hidden="true">↗</span><div><strong>Ubicación flexible</strong><p>CDMX, Guadalajara y remoto USA</p></div></div><div className="info-callout"><strong>¿Algo no coincide?</strong><p>La información editada aquí tiene prioridad sobre la extracción del documento.</p></div></aside>
  </div>;
}

function PreferencesSection({ draft, update }: { draft: ProfileDraft; update: <K extends keyof ProfileDraft>(key: K, value: ProfileDraft[K]) => void }) {
  const weightsTotal = draft.weightSkills + draft.weightExperience + draft.weightLocation + draft.weightMode;
  return <div id="preferences-panel" className="content-grid preferences-grid" role="tabpanel" aria-labelledby="tab-preferences" tabIndex={0}><section className="panel" aria-labelledby="preferences-title"><p className="card-kicker">Criterios de búsqueda</p><h2 id="preferences-title">Qué oportunidades quieres ver</h2><div className="form-grid"><label>Ubicaciones<input name="locations" autoComplete="address-level2" value={draft.locations} onChange={(event) => update("locations", event.target.value)} /><small>Usa comas para agregar varias.</small></label><label>Modalidad<select name="workMode" value={draft.mode} onChange={(event) => update("mode", event.target.value as WorkMode)}><option>Remoto</option><option>Híbrido</option><option>Presencial</option></select></label><label>Salario mínimo (MXN)<input name="minSalary" type="number" min="0" step="1000" value={draft.minSalary} onChange={(event) => update("minSalary", event.target.value)} /></label><label>Salario máximo (MXN)<input name="maxSalary" type="number" min="0" step="1000" value={draft.maxSalary} onChange={(event) => update("maxSalary", event.target.value)} /></label><label className="wide">Autorización de trabajo<textarea name="authorization" autoComplete="off" rows={2} value={draft.authorization} onChange={(event) => update("authorization", event.target.value)} /></label></div><fieldset className="constraints"><legend>Restricciones</legend><label className="checkbox-row"><input name="excludeNoSalary" type="checkbox" defaultChecked />Excluir ofertas sin rango salarial</label><label className="checkbox-row"><input name="excludeUnverified" type="checkbox" defaultChecked />Excluir empresas sin información verificable</label><label className="checkbox-row"><input name="allowRelocation" type="checkbox" />Mostrar ofertas que requieren reubicación</label></fieldset></section><section className="panel weights-panel" aria-labelledby="weights-title"><div className="panel-heading"><div><p className="card-kicker">Compatibilidad</p><h3 id="weights-title">Pesos de evaluación</h3></div><span>{weightsTotal}% asignado</span></div><p className="muted">Ajusta cómo ponderamos cada dimensión al calcular tu compatibilidad.</p><div className="weights-stack"><Weight label="Habilidades" name="weightSkills" value={draft.weightSkills} onChange={(v) => update("weightSkills", v)} /><Weight label="Experiencia" name="weightExperience" value={draft.weightExperience} onChange={(v) => update("weightExperience", v)} /><Weight label="Ubicación" name="weightLocation" value={draft.weightLocation} onChange={(v) => update("weightLocation", v)} /><Weight label="Modalidad" name="weightMode" value={draft.weightMode} onChange={(v) => update("weightMode", v)} /></div><div className="info-callout"><strong>Pesos asignados: {weightsTotal}%</strong><p>{weightsTotal !== 100 ? "Los pesos deberían sumar 100% para una evaluación balanceada." : "Distribución balanceada."}</p></div></section></div>;
}

function Weight({ label, name, value, onChange }: { label: string; name: string; value: number; onChange: (value: number) => void }) {
  return <label className="weight-row"><span><strong>{label}</strong><output>{value}%</output></span><input name={name} aria-label={`Peso de ${label}`} autoComplete="off" type="range" min="0" max="100" step="5" value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}

export default App;
