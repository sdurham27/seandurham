import { SetlistRequest } from "../lib/api";

interface Props {
  form: SetlistRequest;
  onChange: (next: SetlistRequest) => void;
  onGenerate: () => void;
  loading: boolean;
}

export function SetupPanel({ form, onChange, onGenerate, loading }: Props) {
  function set<K extends keyof SetlistRequest>(key: K, value: SetlistRequest[K]) {
    onChange({ ...form, [key]: value });
  }

  return (
    <aside className="setup-panel">
      <p className="panel-title">Event Setup</p>

      <div className="form-group">
        <label>Set length (minutes)</label>
        <input
          type="number"
          min={15}
          max={360}
          value={form.duration_minutes}
          onChange={(e) => set("duration_minutes", Number(e.target.value))}
        />
      </div>

      <div className="form-group">
        <label>Genre focus</label>
        <input
          type="text"
          placeholder="e.g. Techno, House, Drum and Bass…"
          value={form.genre_focus}
          onChange={(e) => set("genre_focus", e.target.value)}
        />
      </div>

      <div className="form-group">
        <label>Vibe / mood goal</label>
        <textarea
          placeholder="e.g. dark and hypnotic building to euphoric, warehouse energy"
          value={form.vibe_goal}
          onChange={(e) => set("vibe_goal", e.target.value)}
        />
      </div>

      <div className="form-group">
        <label>Time of night</label>
        <select
          value={form.time_of_night}
          onChange={(e) =>
            set("time_of_night", e.target.value as SetlistRequest["time_of_night"])
          }
        >
          <option value="warmup">Warmup</option>
          <option value="peak">Peak hour</option>
          <option value="closing">Closing</option>
        </select>
      </div>

      <div className="toggle-row">
        <div>
          <div className="toggle-label">Include unvetted tracks</div>
          <div className="toggle-desc">Tracks Spotify couldn't identify</div>
        </div>
        <label className="toggle">
          <input
            type="checkbox"
            checked={form.include_unvetted}
            onChange={(e) => set("include_unvetted", e.target.checked)}
          />
          <span className="slider" />
        </label>
      </div>

      <button
        className="btn btn-primary"
        onClick={onGenerate}
        disabled={loading}
      >
        {loading ? <><span className="spinner" /> Generating…</> : "Generate Setlist"}
      </button>
    </aside>
  );
}
