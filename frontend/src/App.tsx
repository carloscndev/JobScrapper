import { useCallback, useEffect, useRef, useState } from "react";
import { ApiRequestError, createApiClient, type ExecutionSummary, type HealthStatus, type JobDetailResponse, type JobSummary, type OperationsHealth, type OperationsMetrics, type SourceAdapterName, type SourceRunSummary, type SourceSummary } from "./api/client";
import "./styles.css";

type Section = "profile" | "preferences" | "vacancies" | "operations";
type WorkMode = "Remote" | "Hybrid" | "On-site";

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
  excludeNoSalary: boolean;
  excludeUnverified: boolean;
  allowRelocation: boolean;
}

/** Constraint tokens consumed by backend/app/matching.py. */
const CONSTRAINT_NO_SALARY = "no_salary";
const CONSTRAINT_UNVERIFIED_COMPANY = "unverified_company";
const CONSTRAINT_RELOCATION_REQUIRED = "relocation_required";

const MODALITY_MAP: Record<string, string> = { remote: "Remote", hybrid: "Hybrid", onsite: "On-site", unknown: "Not specified" };

function mapModality(m: string): string {
  return MODALITY_MAP[m.toLowerCase()] ?? m;
}

function mapStatus(s: string): "new" | "changed" | "inactive" | "pending" {
  if (s === "active") return "new";
  if (s === "inactive") return "inactive";
  return "pending";
}

function statusLabel(s: string): string {
  const labels: Record<string, string> = { new: "New", changed: "Changed", inactive: "Inactive", pending: "Pending", active: "Active" };
  return labels[s.toLowerCase()] ?? s;
}

const initialDraft: ProfileDraft = {
  name: "Carlos Castañeda",
  headline: "Senior Software Engineer",
  skills: "Python, TypeScript, React, FastAPI, SQL",
  experience: "API and web product design for 8 years.",
  languages: "Spanish (native), English (C1)",
  education: "Computer Systems Engineering",
  locations: "Mexico City, Guadalajara, Remote (USA)",
  mode: "Hybrid",
  authorization: "Mexico; authorized to work with US teams",
  minSalary: "55000",
  maxSalary: "90000",
  weightSkills: 40,
  weightExperience: 30,
  weightLocation: 20,
  weightMode: 10,
  excludeNoSalary: true,
  excludeUnverified: true,
  allowRelocation: false,
};

const apiClient = createApiClient();

async function requestHealth() {
  const response = await apiClient.getHealth();
  return response;
}

const SOURCE_ADAPTERS: Array<{ value: SourceAdapterName; label: string; kind: "api" | "career_page"; fixtureLabel: string; fixtureHint: string }> = [
  { value: "json-api-feed", label: "JSON API or feed", kind: "api", fixtureLabel: "JSON payload", fixtureHint: "Non-empty object with jobs or data; each opening requires description_url or url." },
  { value: "greenhouse-career-page", label: "Greenhouse", kind: "career_page", fixtureLabel: "Page HTML", fixtureHint: "Static HTML with article/li cards and job-opening links." },
  { value: "lever-career-page", label: "Lever", kind: "career_page", fixtureLabel: "Page HTML", fixtureHint: "Static HTML with article/li cards and job-opening links." },
];

const TAB_SECTIONS: Section[] = ["vacancies", "profile", "preferences", "operations"];

function validateSourceFixture(adapter: SourceAdapterName, fixture: string): string | null {
  if (adapter === "json-api-feed") {
    let payload: unknown;
    try {
      payload = JSON.parse(fixture);
    } catch {
      return "The payload must be valid JSON.";
    }
    if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
      return "The payload must be a JSON object with jobs or data.";
    }
    const record = payload as Record<string, unknown>;
    const jobs = Array.isArray(record.jobs) ? record.jobs : undefined;
    const data = Array.isArray(record.data) ? record.data : undefined;
    const items = jobs ?? data;
    if (!items || items.length === 0) {
      return "The payload must include a jobs or data list with at least one opening.";
    }
    const invalidIndex = items.findIndex((item) => {
      if (typeof item !== "object" || item === null || Array.isArray(item)) return true;
      const job = item as Record<string, unknown>;
      const url = job.description_url ?? job.url;
      return typeof url !== "string" || url.trim().length === 0;
    });
    if (invalidIndex >= 0) {
      return `Opening ${invalidIndex + 1} must include description_url or url.`;
    }
    return null;
  }

  const cardPattern = /<(article|li)\b[^>]*>[\s\S]*?<a\b[^>]*href\s*=\s*["'][^"']+["'][^>]*>[\s\S]*?<\/\1>/i;
  if (!cardPattern.test(fixture)) {
    return "The HTML must include at least one article/li card with a job-opening link.";
  }
  return null;
}

function App() {
  const [section, setSection] = useState<Section>("profile");
  const [draft, setDraft] = useState<ProfileDraft>(initialDraft);
  const [health, setHealth] = useState<HealthStatus>("unavailable");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [connectionMessage, setConnectionMessage] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [cvName, setCvName] = useState("CV_Carlos_Castaneda.pdf");
  const [profileId, setProfileId] = useState<number | null>(null);
  const [profileVersion, setProfileVersion] = useState(1);
  const [profileError, setProfileError] = useState<string | null>(null);
  const healthRequestRef = useRef<ReturnType<typeof requestHealth> | null>(null);

  const refreshHealth = async (announce = true) => {
    setIsRefreshing(true);
    if (announce) setConnectionMessage("Checking the API connection…");
    const request = healthRequestRef.current ?? requestHealth();
    healthRequestRef.current = request;
    try {
      const response = await request;
      const connected = response.status === "ok";
      setHealth(connected ? "ok" : "unavailable");
      if (announce) setConnectionMessage(connected ? "Connection successful. The API is online." : "Connection failed. The API reported an unhealthy status.");
    } catch {
      setHealth("unavailable");
      if (announce) setConnectionMessage("Connection failed. The API could not be reached.");
    } finally {
      setIsRefreshing(false);
      if (healthRequestRef.current === request) healthRequestRef.current = null;
    }
  };

  useEffect(() => { void refreshHealth(false); }, []);

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
            mode: (p.preferences?.modalities?.[0] === "remote" ? "Remote" : p.preferences?.modalities?.[0] === "hybrid" ? "Hybrid" : p.preferences?.modalities?.[0] === "onsite" ? "On-site" : initialDraft.mode) as WorkMode,
            authorization: p.preferences?.work_authorization?.join(", ") || initialDraft.authorization,
            minSalary: p.preferences?.salary_min?.toString() || initialDraft.minSalary,
            maxSalary: p.preferences?.salary_max?.toString() || initialDraft.maxSalary,
            weightSkills: (p.preferences?.weights as Record<string, number>)?.skills ?? initialDraft.weightSkills,
            weightExperience: (p.preferences?.weights as Record<string, number>)?.experience ?? initialDraft.weightExperience,
            weightLocation: (p.preferences?.weights as Record<string, number>)?.location ?? initialDraft.weightLocation,
            weightMode: (p.preferences?.weights as Record<string, number>)?.modality ?? initialDraft.weightMode,
            excludeNoSalary: p.preferences?.excluded_constraints?.includes(CONSTRAINT_NO_SALARY) ?? initialDraft.excludeNoSalary,
            excludeUnverified: p.preferences?.excluded_constraints?.includes(CONSTRAINT_UNVERIFIED_COMPANY) ?? initialDraft.excludeUnverified,
            allowRelocation: p.preferences?.willing_to_relocate ?? !(p.preferences?.excluded_constraints?.includes(CONSTRAINT_RELOCATION_REQUIRED) ?? !initialDraft.allowRelocation),
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
    } catch { setProfileError("The resume could not be uploaded."); }
  };

  const save = async () => {
    if (!profileId) { setProfileError("Upload a resume before saving."); return; }
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
        const updated = await apiClient.updateProfilePreferences(profileId, {
          locations: draft.locations.split(",").map((s) => s.trim()).filter(Boolean),
          modalities: [draft.mode === "Remote" ? "remote" : draft.mode === "Hybrid" ? "hybrid" : "onsite"],
          salary_min: parseInt(draft.minSalary) || undefined,
          salary_max: parseInt(draft.maxSalary) || undefined,
          work_authorization: draft.authorization ? [draft.authorization] : undefined,
          willing_to_relocate: draft.allowRelocation,
          excluded_constraints: [
            ...(draft.excludeNoSalary ? [CONSTRAINT_NO_SALARY] : []),
            ...(draft.excludeUnverified ? [CONSTRAINT_UNVERIFIED_COMPANY] : []),
            ...(!draft.allowRelocation ? [CONSTRAINT_RELOCATION_REQUIRED] : []),
          ],
          weights: { skills: draft.weightSkills, experience: draft.weightExperience, location: draft.weightLocation, modality: draft.weightMode },
        });
        setProfileVersion(updated.version);
        if (updated.preferences) {
          const persistedConstraints = updated.preferences.excluded_constraints ?? [];
          setDraft((current) => ({
            ...current,
            excludeNoSalary: persistedConstraints.includes(CONSTRAINT_NO_SALARY),
            excludeUnverified: persistedConstraints.includes(CONSTRAINT_UNVERIFIED_COMPANY),
            allowRelocation: updated.preferences?.willing_to_relocate ?? !persistedConstraints.includes(CONSTRAINT_RELOCATION_REQUIRED),
          }));
        }
      }
      setSaved(true);
    } catch { setProfileError("Changes could not be saved."); }
    finally { setSaving(false); }
  };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="topbar">
        <a className="brand" href="/" aria-label="JobScrapper, home"><span className="brand-mark" aria-hidden="true">J</span><span>JobScrapper</span></a>
        <div className="topbar-meta"><span className="environment-badge">Local</span><span className={`service-status ${health === "ok" ? "online" : ""}`}><span aria-hidden="true" />{health === "ok" ? "API connected" : "API pending"}</span></div>
      </header>

      <main className="main-content" aria-labelledby="page-title" id="main-content">
        <div className="page-heading"><div><p className="eyebrow">Configuration</p><h1 id="page-title">Your search profile</h1><p className="hero-copy">Review what we extracted from your resume and adjust what makes an opening relevant.</p></div><button type="button" className="secondary-button compact" onClick={() => void refreshHealth()} disabled={isRefreshing} aria-busy={isRefreshing}>{isRefreshing ? "Checking…" : "Check connection"}</button></div>
        {connectionMessage && <p className={`connection-feedback ${isRefreshing ? "checking" : health === "ok" ? "success" : "failure"}`} role="status" aria-live="polite">{connectionMessage}</p>}

        <nav className="tabs" role="tablist" aria-label="Profile sections">
          <button id="tab-vacancies" role="tab" type="button" className={section === "vacancies" ? "tab active" : "tab"} aria-controls="vacancies-panel" aria-selected={section === "vacancies"} tabIndex={section === "vacancies" ? 0 : -1} onKeyDown={handleTabKeyDown} onClick={() => setSection("vacancies")}>Openings</button>
          <button id="tab-profile" role="tab" type="button" className={section === "profile" ? "tab active" : "tab"} aria-controls="profile-panel" aria-selected={section === "profile"} tabIndex={section === "profile" ? 0 : -1} onKeyDown={handleTabKeyDown} onClick={() => setSection("profile")}>Resume and profile</button>
          <button id="tab-preferences" role="tab" type="button" className={section === "preferences" ? "tab active" : "tab"} aria-controls="preferences-panel" aria-selected={section === "preferences"} tabIndex={section === "preferences" ? 0 : -1} onKeyDown={handleTabKeyDown} onClick={() => setSection("preferences")}>Preferences and weights</button>
          <button id="tab-operations" role="tab" type="button" className={section === "operations" ? "tab active" : "tab"} aria-controls="operations-panel" aria-selected={section === "operations"} tabIndex={section === "operations" ? 0 : -1} onKeyDown={handleTabKeyDown} onClick={() => setSection("operations")}>Operations</button>
        </nav>

        {profileError && <div className="error-callout" role="alert"><strong>Error</strong><span>{profileError}</span></div>}

        {section === "vacancies" ? <VacancyDashboard /> : section === "operations" ? <OperationsDashboard /> : section === "profile" ? <ProfileSection draft={draft} cvName={cvName} onUpload={handleCvUpload} update={update} /> : <PreferencesSection draft={draft} update={update} />}

        {(section === "profile" || section === "preferences") && <div className="save-bar"><div aria-live="polite"><strong>{saved ? "Changes saved" : `Profile version ${profileVersion}`}</strong><span>{profileId ? (saved ? "Your next evaluation will use this configuration." : "Changes will create a new version and reevaluate the openings.") : "Upload a resume to begin."}</span></div><button type="button" className="primary-button" onClick={save} disabled={saving}>{saving ? "Saving…" : saved ? "Saved" : "Save changes"}</button></div>}
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
  const [errorFields, setErrorFields] = useState<Array<{ field?: string; message?: string }>>([]);
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
  const [sourcePendingActivation, setSourcePendingActivation] = useState<SourceSummary | null>(null);
  const [termsChecked, setTermsChecked] = useState(false);
  const [activationError, setActivationError] = useState<string | null>(null);

  const setOperationError = (caught: unknown, fallback: string) => {
    setError(caught instanceof ApiRequestError ? caught.message : fallback);
    setErrorFields(caught instanceof ApiRequestError ? caught.fields : []);
  };

  const load = async () => {
    setLoading(true); setError(null); setErrorFields([]);
    try {
      const [nextSources, nextExecutions, nextMetrics, nextHealth] = await Promise.all([apiClient.getSources(), apiClient.getExecutions(), apiClient.getMetrics(), apiClient.getOperationsHealth()]);
      setSources(nextSources); setExecutions(nextExecutions); setMetrics(nextMetrics); setOperationsHealth(nextHealth); setLastUpdated(new Date().toISOString());
    } catch (caught) { setOperationError(caught, "We could not query the API."); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);

  const manualRefresh = async () => {
    setRefreshing(true); setError(null); setErrorFields([]);
    try { const run = await apiClient.refresh(); setExecutions((current) => [run, ...current].slice(0, 10)); setLastUpdated(new Date().toISOString()); }
    catch (caught) { setOperationError(caught, "The refresh could not start. Check whether a run is already in progress."); }
    finally { setRefreshing(false); }
  };

  const toggleSource = async (id: number, current: boolean) => {
    const source = sources.find((item) => item.id === id);
    if (!current && source?.config?.terms_accepted !== true) {
      if (!source) return;
      setSourcePendingActivation(source);
      setTermsChecked(false);
      setActivationError(null);
      return;
    }
    try {
      await apiClient.updateSource(id, current ? { enabled: false } : { enabled: true, config: { terms_accepted: true } });
      void load();
    } catch (caught) { setOperationError(caught, "The source status could not be changed."); }
  };

  const cancelActivation = () => {
    setSourcePendingActivation(null);
    setTermsChecked(false);
    setActivationError(null);
  };

  const activatePendingSource = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!sourcePendingActivation || !termsChecked) return;
    setActivationError(null);
    try {
      await apiClient.updateSource(sourcePendingActivation.id, { enabled: true, config: { terms_accepted: true } });
      cancelActivation();
      void load();
    } catch (caught) {
      const detail = caught instanceof ApiRequestError
        ? [caught.message, ...caught.fields.map((field) => `${field.field ?? "Field"}: ${field.message ?? "review this value"}`)].join(" ")
        : "The source could not be activated. Review the configuration and try again.";
      setActivationError(detail);
    }
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
    if (!name) { setFormError("Enter a source name."); return; }
    if (!formTermsAccepted) { setFormError("You must accept the source terms of use before activating it."); return; }
    if (formMode === "network" && !url) { setFormError("The base URL is required in network mode."); return; }
    if (formMode === "fixture" && !fixture) { setFormError(`Add ${adapter.fixtureLabel.toLowerCase()} or switch to network mode.`); return; }
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
      setFormError(caught instanceof ApiRequestError ? caught.message : "The source could not be created.");
      setFormErrorFields(caught instanceof ApiRequestError ? caught.fields : []);
    }
  };

  const deleteSource = async (id: number, name: string) => {
    if (!confirm(`Delete source "${name}"?`)) return;
    try { await apiClient.deleteSource(id); void load(); }
    catch (caught) { setOperationError(caught, "The source could not be deleted."); }
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
    <div className="dashboard-heading"><div><p className="eyebrow">Operations center</p><h2>Search status</h2><p className="hero-copy">Monitor sources, runs, and the health of your local integrations.</p></div><button type="button" className="primary-button" onClick={manualRefresh} disabled={refreshing} aria-busy={refreshing}>{refreshing ? "Refreshing…" : "Refresh openings"}</button></div>
    {error && <div className="error-callout" role="alert"><strong>Error</strong><span>{error}</span>{errorFields.length > 0 && <ul className="form-error-list">{errorFields.map((field, index) => <li key={`${field.field ?? "error"}-${index}`}><strong>{field.field ?? "Review this field"}:</strong> {field.message ?? "Correct this value and try again."}</li>)}</ul>}<button type="button" className="secondary-button compact" onClick={() => void load()}>Retry</button></div>}
    {sourcePendingActivation && <div className="activation-dialog-backdrop"><form className="activation-dialog" role="dialog" aria-modal="true" aria-labelledby="activation-dialog-title" aria-describedby="activation-dialog-description" onSubmit={activatePendingSource}><h3 id="activation-dialog-title">Confirm activation</h3><p id="activation-dialog-description">Review the terms before activating <strong>{sourcePendingActivation.name}</strong>.</p>{sourcePendingActivation.terms_url ? <a className="activation-terms-link" href={sourcePendingActivation.terms_url} target="_blank" rel="noopener noreferrer">Open terms of use<span aria-hidden="true"> ↗</span></a> : <p className="activation-no-terms">This source has no registered terms URL.</p>}<label className="checkbox-row activation-check" htmlFor="activation-terms-check"><input id="activation-terms-check" type="checkbox" checked={termsChecked} onChange={(event) => setTermsChecked(event.target.checked)} required autoFocus />I confirm that I reviewed and accept the terms of use.</label>{activationError && <div className="error-callout activation-error" role="alert">{activationError}</div>}<div className="activation-actions"><button type="button" className="secondary-button" onClick={cancelActivation}>Cancel</button><button type="submit" className="primary-button" disabled={!termsChecked}>Activate source</button></div></form></div>}
    {loading ? <div className="loading-state" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" />Loading operations status…</div> : <>
      <div className="ops-metrics" aria-label="Operations metrics"><Metric label="Active openings" value={totalJobs} hint={`${totalJobsRegistered} registered`} /><Metric label="Runs" value={totalExecutions} hint={`${runningExecutions} in progress`} /><Metric label="Active sources" value={sources.filter((s) => s.enabled).length} hint={`${sources.length} configured`} /><Metric label="Last refresh" value={lastUpdated ? new Date(lastUpdated).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }) : "—"} hint="local time" /></div>
      <div className="operations-grid">
        <section className="panel" aria-labelledby="sources-title">
          <div className="panel-heading"><div><p className="card-kicker">Ingestion</p><h3 id="sources-title">Connected sources</h3></div><span className="source-count">{sources.filter((s) => s.enabled).length}/{sources.length} active</span></div>
          <p className="muted">Activate or pause a source without losing its configuration.</p>
          {sources.length ? <ul className="source-list">{sources.map((source) => {
            const run = source.enabled ? latestSourceRuns.get(source.id) : undefined;
            const runClass = source.enabled ? (run?.status === "success" ? "healthy" : run ? "failed" : "unknown") : "paused";
            const runLabel = source.enabled ? (run ? `Latest run: ${run.status}` : "No runs") : "Paused";
            return <li key={source.id}>
              <div className="source-details"><strong>{source.name}</strong><span>{source.config?.adapter ?? source.kind} · {source.base_url || "Local fixture"}</span><span className={`source-run-status ${runClass}`} aria-label={runLabel}>{source.enabled ? (run ? `${run.status} · ${run.jobs_found} openings` : "No runs") : "Paused"}</span>{source.enabled && run?.error && <span className="source-error" title={run.error}>{run.error}</span>}</div>
              <div className="source-actions"><button type="button" className={`toggle ${source.enabled ? "on" : ""}`} aria-pressed={source.enabled} onClick={() => toggleSource(source.id, source.enabled)}><span aria-hidden="true" />{source.enabled ? "Active" : "Paused"}</button><button type="button" className="toggle danger" onClick={() => deleteSource(source.id, source.name)}>Delete</button></div>
            </li>;
          })}</ul> : <div className="empty-state"><strong>No sources are configured.</strong><span>Add a source to start searching.</span></div>}
          <button type="button" className="secondary-button compact" style={{ marginTop: "0.75rem" }} onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Add source"}</button>
          {showForm && <form onSubmit={createSource} className="source-form">
            <p className="source-form-intro">Configure a complete source so the next refresh can run it.</p>
            {formError && <div className="error-callout" role="alert"><strong>Not created</strong><span>{formError}</span>{formErrorFields.length > 0 && <ul className="form-error-list">{formErrorFields.map((field, index) => <li key={`${field.field ?? "error"}-${index}`}><strong>{field.field ?? "Review this field"}:</strong> {field.message ?? "Correct this value and try again."}</li>)}</ul>}</div>}
            <label htmlFor="source-name">Name<input id="source-name" name="sourceName" autoComplete="organization" value={formName} onChange={(e) => setFormName(e.target.value)} required placeholder="Example: Greenhouse Acme" /></label>
            <label htmlFor="source-adapter">Adapter<select id="source-adapter" name="sourceAdapter" autoComplete="off" value={formAdapter} onChange={(e) => setFormAdapter(e.target.value as SourceAdapterName)} aria-describedby="adapter-hint">{SOURCE_ADAPTERS.map((adapter) => <option key={adapter.value} value={adapter.value}>{adapter.label}</option>)}</select><small id="adapter-hint">The adapter determines the format to read.</small></label>
            <label htmlFor="source-mode">Ingestion mode<select id="source-mode" name="sourceMode" autoComplete="off" value={formMode} onChange={(e) => setFormMode(e.target.value as "fixture" | "network")}><option value="fixture">Local fixture (recommended for testing)</option><option value="network">Network (queries the URL)</option></select></label>
            <label htmlFor="source-base-url">Base URL{formMode === "network" ? <input id="source-base-url" name="baseUrl" autoComplete="url" value={formUrl} onChange={(e) => setFormUrl(e.target.value)} required placeholder="https://example.com/jobs" type="url" /> : <input id="source-base-url" name="baseUrl" autoComplete="url" value={formUrl} onChange={(e) => setFormUrl(e.target.value)} placeholder="Optional: used to resolve relative links" type="url" />}<small>{formMode === "network" ? "Must be an accessible HTTP(S) URL permitted by robots.txt." : "Optional in fixture mode."}</small></label>
            <label htmlFor="source-terms-url">Terms-of-use URL<input id="source-terms-url" name="termsUrl" autoComplete="url" value={formTermsUrl} onChange={(e) => setFormTermsUrl(e.target.value)} placeholder="https://example.com/terms" type="url" /><small>Save the reference you reviewed before enabling the source.</small></label>
            <label htmlFor="source-fixture">{selectedAdapter.fixtureLabel}{formMode === "fixture" && <textarea id="source-fixture" name="fixture" autoComplete="off" value={formFixture} onChange={(e) => setFormFixture(e.target.value)} required rows={selectedAdapter.value === "json-api-feed" ? 6 : 5} placeholder={selectedAdapter.value === "json-api-feed" ? '{"jobs": [{"title": "...", "description_url": "https://..."}]}' : "<article data-job=\"true\">...</article>"} />}<small>{formMode === "fixture" ? selectedAdapter.fixtureHint : "No fixture is needed in network mode."}</small></label>
            <label className="checkbox-row source-terms" htmlFor="source-terms-accepted"><input type="checkbox" checked={formTermsAccepted} onChange={(e) => setFormTermsAccepted(e.target.checked)} required id="source-terms-accepted" name="termsAccepted" autoComplete="off" />I confirm that I reviewed and accept this source's terms of use.</label>
            <button type="submit" className="primary-button">Create executable source</button>
          </form>}
        </section>
        <section className="panel" aria-labelledby="health-title"><div className="panel-heading"><div><p className="card-kicker">Availability</p><h3 id="health-title">Service health</h3></div><span className={`health-badge ${healthy ? "healthy" : "degraded"}`}><i aria-hidden="true" />{healthy ? "Healthy" : "Review"}</span></div><ul className="health-list">{Object.entries(operationsHealth?.checks ?? { api: { status: "local" }, database: { status: "local" }, ollama: { status: "optional" }, notion: { status: "optional" } }).map(([name, check]) => <li key={name}><span>{name === "api" ? "API" : name === "database" ? "SQLite" : name === "ollama" ? "Local model" : "Notion"}</span><strong className={check.status === "ok" || check.status === "local" ? "ok" : "muted-status"}>{check.status}</strong></li>)}</ul></section>
      </div>
      <section className="panel execution-panel" aria-labelledby="executions-title"><div className="panel-heading"><div><p className="card-kicker">History</p><h3 id="executions-title">Latest runs</h3></div><span className="muted">{executions.length} shown</span></div>{executions.length ? <div className="execution-table-wrap"><table><caption className="sr-only">Search run history</caption><thead><tr><th scope="col">Status</th><th scope="col">Start</th><th scope="col">Openings</th><th scope="col">Errors</th></tr></thead><tbody>{executions.map((run) => <tr key={run.run_id}><td><span className={`run-status ${run.status}`}>{run.status}</span></td><td>{run.started_at ? new Date(run.started_at).toLocaleString("en-US") : "—"}</td><td>{run.metrics.jobs_found ?? 0}</td><td>{run.metrics.sources_failed ?? (run.error ? 1 : 0)}</td></tr>)}</tbody></table></div> : <div className="empty-state"><strong>There are no runs yet.</strong><span>Use “Refresh openings” to start the first one.</span></div>}</section>
    </>}
  </section>;
}

function Metric({ label, value, hint, accent = false }: { label: string; value: number | string; hint: string; accent?: boolean }) { return <div className={`metric-card ${accent ? "accent" : ""}`}><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>; }

function VacancyDashboard() {
  const [region, setRegion] = useState("all");
  const [modality, setModality] = useState("all");
  const [status, setStatus] = useState("all");
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
        region: region === "all" ? undefined : region,
        modality: modality === "all" ? undefined : modality,
        status: status === "all" ? undefined : status,
        company: company || undefined,
        min_score: minScore || undefined,
        order: orderMap[sort],
        direction: "desc",
      });
      setJobs(result.items); setTotal(result.total); setTotalPages(result.total_pages);
    } catch { setError("We could not load the openings."); }
    finally { setLoading(false); }
  }, [region, modality, status, company, minScore, sort, page]);

  useEffect(() => { void fetchJobs(); }, [fetchJobs]);
  useEffect(() => { setPage(1); }, [region, modality, status, company, minScore, sort]);

  if (selectedJobId) return <VacancyDetail jobId={selectedJobId} onBack={() => setSelectedJobId(null)} />;

  return <section id="vacancies-panel" className="vacancy-dashboard" role="tabpanel" aria-labelledby="tab-vacancies" tabIndex={0}>
    <div className="dashboard-heading"><div><p className="eyebrow">Smart search</p><h2>Openings for you</h2><p className="hero-copy">{total} compatible opportunities, continuously updated.</p></div><button type="button" className="secondary-button" onClick={() => void fetchJobs()}>Refresh openings</button></div>
    <div className="filter-panel" aria-label="Opening filters"><label>Region<select value={region} onChange={(e) => setRegion(e.target.value)}><option value="all">All</option><option value="cdmx">CDMX</option><option value="guadalajara">Guadalajara</option><option value="usa">USA</option><option value="mexico">Mexico</option><option value="other">Other</option></select></label><label>Work arrangement<select value={modality} onChange={(e) => setModality(e.target.value)}><option value="all">All</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="onsite">On-site</option></select></label><label>Minimum score<output className="range-output">{minScore}%</output><input aria-label="Minimum score" type="range" min="0" max="100" step="5" value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} /></label><label>Company<input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Search company" /></label><label>Status<select value={status} onChange={(e) => setStatus(e.target.value)}><option value="all">All</option><option value="active">New</option><option value="inactive">Inactive</option></select></label><label>Sort by<select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}><option value="score">Compatibility</option><option value="date">Most recent</option><option value="company">Company A-Z</option></select></label></div>
    <div className="status-legend" aria-label="Opening statuses">{([["new", "New"], ["inactive", "Inactive"], ["active", "Active"]] as const).map(([key, label]) => <span key={key}><i className={`status-dot ${key}`} aria-hidden="true" />{label}</span>)}</div>
    {error && <div className="error-callout" role="alert"><strong>Error</strong><span>{error}</span><button type="button" className="secondary-button compact" onClick={() => void fetchJobs()}>Retry</button></div>}
    {loading ? <div className="loading-state" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" />Loading openings…</div> : <div className="vacancy-list" aria-live="polite">{jobs.length ? jobs.map((job) => <article className="vacancy-card" key={job.id}><button type="button" className="vacancy-card-button" onClick={() => setSelectedJobId(job.id)} aria-label={`View details for ${job.title} at ${job.company}`}><div className="vacancy-main"><div className="vacancy-title-row"><h3>{job.title}</h3><span className={`status-pill ${mapStatus(job.status)}`}>{statusLabel(job.status)}</span></div><p className="vacancy-company">{job.company} · {job.region} · {mapModality(job.modality)}</p><p className="vacancy-meta">{job.published_at ? `Published ${job.published_at}` : ""}</p></div><div className="score-badge" aria-label={`${job.score ?? "N/A"}% compatibility`}><strong>{job.score != null ? `${job.score}%` : "—"}</strong><span>match</span></div></button></article>) : <div className="empty-state"><strong>No openings match these filters.</strong><span>Try broadening the region or lowering the minimum score.</span></div>}</div>}
    <div className="pagination" aria-label="Pagination"><span>Showing {jobs.length ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, total)} of {total}</span><div><button type="button" className="secondary-button compact" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button><span className="page-number">Page {page} of {Math.max(1, totalPages)}</span><button type="button" className="secondary-button compact" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</button></div></div>
  </section>;
}

function VacancyDetail({ jobId, onBack }: { jobId: number; onBack: () => void }) {
  const [detail, setDetail] = useState<JobDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { apiClient.getJobDetail(jobId).then(setDetail).finally(() => setLoading(false)); }, [jobId]);

  if (loading) return <section className="vacancy-detail" aria-labelledby="vacancy-detail-title"><button type="button" className="secondary-button compact detail-back" onClick={onBack}>← Back to openings</button><div className="loading-state" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" />Loading details…</div></section>;
  if (!detail) return <section className="vacancy-detail" aria-labelledby="vacancy-detail-title"><button type="button" className="secondary-button compact detail-back" onClick={onBack}>← Back to openings</button><div className="error-callout" role="alert">The details could not be loaded.</div></section>;

  const salary = detail.salary_min != null && detail.salary_max != null ? `$${detail.salary_min?.toLocaleString()}–$${detail.salary_max?.toLocaleString()} ${detail.salary_currency ?? ""}/year` : "Not specified";
  const gaps = (detail.evaluation?.gaps ?? []) as string[];
  const recommendations = (detail.recommendations ?? []) as string[];

  return <section className="vacancy-detail" aria-labelledby="vacancy-detail-title"><button type="button" className="secondary-button compact detail-back" onClick={onBack}>← Back to openings</button><div className="detail-header"><div><p className="eyebrow">Opening details</p><h2 id="vacancy-detail-title">{detail.title}</h2><p className="vacancy-company">{detail.company} · {detail.region}</p></div><div className="detail-score" aria-label={`${detail.score ?? "N/A"}% compatibility`}><strong>{detail.score != null ? `${detail.score}%` : "—"}</strong><span>compatibility</span></div></div><div className="detail-grid"><div className="detail-main"><section className="panel" aria-labelledby="description-title"><h3 id="description-title">Description</h3><p>{detail.description}</p><dl className="detail-facts"><div><dt>Location</dt><dd>{detail.region}</dd></div><div><dt>Work arrangement</dt><dd>{mapModality(detail.modality)}</dd></div><div><dt>Estimated salary</dt><dd>{salary}</dd></div><div><dt>Published</dt><dd>{detail.published_at ?? "—"}</dd></div></dl></section>{recommendations.length > 0 && <section className="panel" aria-labelledby="recommendations-title"><h3 id="recommendations-title">Recommendations</h3><ul className="detail-list">{recommendations.map((item, i) => <li key={i}>{item}</li>)}</ul></section>}</div><aside className="panel detail-aside" aria-labelledby="match-title"><h3 id="match-title">Compatibility</h3><p className="muted">Match calculated against your current profile.</p>{gaps.length > 0 && <><h4>Detected gaps</h4><ul className="detail-list">{gaps.map((gap, i) => <li key={i}>{gap}</li>)}</ul></>}<div className="detail-actions"><a className="primary-button" href={detail.application_url ?? detail.description_url} target="_blank" rel="noopener noreferrer">Apply<span aria-hidden="true"> ↗</span></a><a className="secondary-button" href={detail.description_url} target="_blank" rel="noopener noreferrer">View original description<span aria-hidden="true"> ↗</span></a></div></aside></div></section>;
}

function ProfileSection({ draft, cvName, onUpload, update }: { draft: ProfileDraft; cvName: string; onUpload: (event: React.ChangeEvent<HTMLInputElement>) => void; update: <K extends keyof ProfileDraft>(key: K, value: ProfileDraft[K]) => void }) {
  return <div id="profile-panel" className="content-grid" role="tabpanel" aria-labelledby="tab-profile" tabIndex={0}>
    <section className="panel" aria-labelledby="cv-title"><div className="panel-heading"><div><p className="card-kicker">Resume extraction</p><h2 id="cv-title">Review and correct your information</h2></div><span className="confidence-badge">92% confidence</span></div><p className="muted">Edit any field before using it to find openings.</p>
      <label className="upload-zone" htmlFor="cv-upload"><span className="upload-icon" aria-hidden="true">↑</span><span><strong>{cvName}</strong><small>PDF · DOCX</small></span><span className="upload-action">Change file</span><input id="cv-upload" name="cvFile" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={onUpload} /></label>
      <div className="form-stack"><label>Name<input name="name" autoComplete="name" value={draft.name} onChange={(event) => update("name", event.target.value)} /></label><label>Professional headline<input name="headline" autoComplete="organization-title" value={draft.headline} onChange={(event) => update("headline", event.target.value)} /></label><label>Key skills<textarea name="skills" autoComplete="off" rows={3} value={draft.skills} onChange={(event) => update("skills", event.target.value)} /><small>Separate skills with commas.</small></label><label>Professional experience<textarea name="experience" autoComplete="off" rows={4} value={draft.experience} onChange={(event) => update("experience", event.target.value)} /></label><label>Languages and education<textarea name="education" autoComplete="off" rows={2} value={`${draft.languages}\n${draft.education}`} onChange={(event) => { const [languages = "", education = ""] = event.target.value.split("\n"); update("languages", languages); update("education", education); }} /></label></div>
    </section>
    <aside className="panel summary-panel" aria-labelledby="summary-title"><p className="card-kicker">Detected summary</p><h2 id="summary-title">How we understand your profile</h2><div className="summary-item"><span className="summary-icon" aria-hidden="true">✦</span><div><strong>Senior profile</strong><p>8 years of experience · Engineering</p></div></div><div className="summary-item"><span className="summary-icon" aria-hidden="true">◎</span><div><strong>5 primary skills</strong><p>Python · TypeScript · React · FastAPI · SQL</p></div></div><div className="summary-item"><span className="summary-icon" aria-hidden="true">↗</span><div><strong>Flexible location</strong><p>CDMX, Guadalajara, and remote USA</p></div></div><div className="info-callout"><strong>Does something not match?</strong><p>Information edited here takes precedence over document extraction.</p></div></aside>
  </div>;
}

function PreferencesSection({ draft, update }: { draft: ProfileDraft; update: <K extends keyof ProfileDraft>(key: K, value: ProfileDraft[K]) => void }) {
  const weightsTotal = draft.weightSkills + draft.weightExperience + draft.weightLocation + draft.weightMode;
  return <div id="preferences-panel" className="content-grid preferences-grid" role="tabpanel" aria-labelledby="tab-preferences" tabIndex={0}><section className="panel" aria-labelledby="preferences-title"><p className="card-kicker">Search criteria</p><h2 id="preferences-title">Which opportunities you want to see</h2><div className="form-grid"><label>Locations<input name="locations" autoComplete="address-level2" value={draft.locations} onChange={(event) => update("locations", event.target.value)} /><small>Use commas to add several.</small></label><label>Work arrangement<select name="workMode" value={draft.mode} onChange={(event) => update("mode", event.target.value as WorkMode)}><option>Remote</option><option>Hybrid</option><option>On-site</option></select></label><label>Minimum salary (MXN)<input name="minSalary" type="number" min="0" step="1000" value={draft.minSalary} onChange={(event) => update("minSalary", event.target.value)} /></label><label>Maximum salary (MXN)<input name="maxSalary" type="number" min="0" step="1000" value={draft.maxSalary} onChange={(event) => update("maxSalary", event.target.value)} /></label><label className="wide">Work authorization<textarea name="authorization" autoComplete="off" rows={2} value={draft.authorization} onChange={(event) => update("authorization", event.target.value)} /></label></div><fieldset className="constraints"><legend>Constraints</legend><label className="checkbox-row"><input name="excludeNoSalary" type="checkbox" autoComplete="off" checked={draft.excludeNoSalary} onChange={(event) => update("excludeNoSalary", event.target.checked)} />Exclude openings without a salary range</label><label className="checkbox-row"><input name="excludeUnverified" type="checkbox" autoComplete="off" checked={draft.excludeUnverified} onChange={(event) => update("excludeUnverified", event.target.checked)} />Exclude companies without verifiable information</label><label className="checkbox-row"><input name="allowRelocation" type="checkbox" autoComplete="off" checked={draft.allowRelocation} onChange={(event) => update("allowRelocation", event.target.checked)} />Show openings that require relocation</label></fieldset></section><section className="panel weights-panel" aria-labelledby="weights-title"><div className="panel-heading"><div><p className="card-kicker">Compatibility</p><h3 id="weights-title">Evaluation weights</h3></div><span>{weightsTotal}% assigned</span></div><p className="muted">Adjust how each dimension is weighted when calculating your compatibility.</p><div className="weights-stack"><Weight label="Skills" name="weightSkills" value={draft.weightSkills} onChange={(v) => update("weightSkills", v)} /><Weight label="Experience" name="weightExperience" value={draft.weightExperience} onChange={(v) => update("weightExperience", v)} /><Weight label="Location" name="weightLocation" value={draft.weightLocation} onChange={(v) => update("weightLocation", v)} /><Weight label="Work arrangement" name="weightMode" value={draft.weightMode} onChange={(v) => update("weightMode", v)} /></div><div className="info-callout"><strong>Assigned weights: {weightsTotal}%</strong><p>{weightsTotal !== 100 ? "Weights should total 100% for a balanced evaluation." : "Balanced distribution."}</p></div></section></div>;
}

function Weight({ label, name, value, onChange }: { label: string; name: string; value: number; onChange: (value: number) => void }) {
  return <label className="weight-row"><span><strong>{label}</strong><output>{value}%</output></span><input name={name} aria-label={`${label} weight`} autoComplete="off" type="range" min="0" max="100" step="5" value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}

export default App;
