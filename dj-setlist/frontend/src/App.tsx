import { useState } from "react";
import { SetupPanel } from "./components/SetupPanel";
import { SetlistPanel } from "./components/SetlistPanel";
import { useLibraryStatus } from "./hooks/useLibraryStatus";
import { generateSetlist, SetlistRequest, SetlistResponse } from "./lib/api";

const DEFAULT_FORM: SetlistRequest = {
  duration_minutes: 60,
  genre_focus: "",
  vibe_goal: "",
  time_of_night: "peak",
  include_unvetted: false,
};

export default function App() {
  const status = useLibraryStatus();
  const [form, setForm] = useState<SetlistRequest>(DEFAULT_FORM);
  const [result, setResult] = useState<SetlistResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const res = await generateSetlist(form);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>DJ Setlist AI</h1>
        <span className="subtitle">rekordbox × Claude</span>
        {status && (
          <div className="status-badges">
            <span className="badge">{status.total_tracks.toLocaleString()} tracks</span>
            <span className={`badge${status.spotify_enriched > 0 ? " green" : ""}`}>
              {status.spotify_enriched.toLocaleString()} Spotify
            </span>
            <span className={`badge${status.ai_tagged > 0 ? " green" : ""}`}>
              {status.ai_tagged.toLocaleString()} AI tagged
            </span>
          </div>
        )}
      </header>

      <div className="panels">
        <SetupPanel
          form={form}
          onChange={setForm}
          onGenerate={handleGenerate}
          loading={loading}
        />
        <SetlistPanel result={result} loading={loading} error={error} />
      </div>
    </div>
  );
}
