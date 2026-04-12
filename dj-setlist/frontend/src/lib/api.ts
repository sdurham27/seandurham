const BASE = "/api";

export interface LibraryStatus {
  total_tracks: number;
  spotify_enriched: number;
  ai_tagged: number;
}

export interface SetlistRequest {
  duration_minutes: number;
  genre_focus: string;
  vibe_goal: string;
  time_of_night: "warmup" | "peak" | "closing";
  include_unvetted: boolean;
  track_count_hint?: number;
}

export interface SetlistTrack {
  id: string;
  title: string;
  artist: string;
  genre: string;
  bpm: number | null;
  camelot_key: string | null;
  rating: number;
  play_count: number;
  energy_level: number | null;
  mood: string | null;
  vibe_tags: string[];
  best_for: string[];
  vetted: boolean;
  valence: number | null;
  energy: number | null;
  reason: string;
}

export interface SetlistResponse {
  setlist: SetlistTrack[];
  arc_description: string;
  duration_minutes: number;
  event: {
    genre_focus: string;
    vibe_goal: string;
    time_of_night: string;
  };
}

export async function fetchLibraryStatus(): Promise<LibraryStatus> {
  const res = await fetch(`${BASE}/library/status`);
  if (!res.ok) throw new Error("Failed to fetch library status");
  return res.json();
}

export async function generateSetlist(req: SetlistRequest): Promise<SetlistResponse> {
  const res = await fetch(`${BASE}/setlist/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Failed to generate setlist");
  }
  return res.json();
}

export async function exportSetlist(playlistName: string, tracks: SetlistTrack[]): Promise<void> {
  const res = await fetch(`${BASE}/setlist/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ playlist_name: playlistName, tracks }),
  });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${playlistName.replace(/\s+/g, "_")}.xml`;
  a.click();
  URL.revokeObjectURL(url);
}
