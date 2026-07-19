import { useEffect, useState } from "react";
import { createApiClient, type HealthStatus } from "./api/client";
import "./styles.css";

const initialHealth: HealthStatus = "unavailable";
const apiClient = createApiClient();

function App() {
  const [health, setHealth] = useState<HealthStatus>(initialHealth);
  const [isRefreshing, setIsRefreshing] = useState(false);

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

  useEffect(() => {
    void refreshHealth();
  }, []);

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="JobScrapper, inicio">
          <span className="brand-mark" aria-hidden="true">J</span>
          <span>JobScrapper</span>
        </a>
        <span className="environment-badge">Local</span>
      </header>

      <main className="main-content">
        <section className="hero" aria-labelledby="page-title">
          <p className="eyebrow">Tu siguiente oportunidad</p>
          <h1 id="page-title">Encuentra empleos que encajan contigo.</h1>
          <p className="hero-copy">
            Configura tu perfil para descubrir oportunidades relevantes en México y Estados Unidos.
          </p>
          <div className="hero-actions">
            <button type="button" className="primary-button" onClick={() => undefined}>
              Configurar mi perfil
            </button>
            <button type="button" className="secondary-button" onClick={refreshHealth} disabled={isRefreshing}>
              {isRefreshing ? "Comprobando…" : "Comprobar conexión"}
            </button>
          </div>
        </section>

        <section className="status-card" aria-labelledby="status-title">
          <div>
            <p className="card-kicker">Estado del servicio</p>
            <h2 id="status-title">Listo para empezar</h2>
            <p className="muted">Las ofertas aparecerán aquí cuando conectes tu perfil.</p>
          </div>
          <div className={`status-indicator ${health === "ok" ? "is-ok" : "is-muted"}`} role="status">
            <span className="status-dot" aria-hidden="true" />
            {health === "ok" ? "API conectada" : "API pendiente"}
          </div>
        </section>

        <section className="feature-grid" aria-label="Próximamente">
          <article className="feature-card"><span aria-hidden="true">01</span><h2>Tu perfil</h2><p>CV, habilidades y preferencias en un solo lugar.</p></article>
          <article className="feature-card"><span aria-hidden="true">02</span><h2>Ofertas relevantes</h2><p>Compatibilidad clara para priorizar tu búsqueda.</p></article>
          <article className="feature-card"><span aria-hidden="true">03</span><h2>Actualización diaria</h2><p>Nuevas oportunidades sin revisar cada portal.</p></article>
        </section>
      </main>
    </div>
  );
}

export default App;
