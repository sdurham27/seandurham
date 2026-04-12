import { useState } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { SetlistTrack, SetlistResponse, exportSetlist } from "../lib/api";
import { TrackRow } from "./TrackRow";

interface Props {
  result: SetlistResponse | null;
  loading: boolean;
  error: string | null;
}

export function SetlistPanel({ result, loading, error }: Props) {
  const [tracks, setTracks] = useState<SetlistTrack[]>([]);
  const [playlistName, setPlaylistName] = useState("AI Setlist");
  const [showReasons, setShowReasons] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Sync from props when new result arrives
  if (result && result.setlist !== tracks && !loading) {
    setTracks(result.setlist);
  }

  const sensors = useSensors(useSensor(PointerSensor));

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      setTracks((items) => {
        const oldIndex = items.findIndex((i) => i.id === active.id);
        const newIndex = items.findIndex((i) => i.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  }

  async function handleExport() {
    if (!tracks.length) return;
    setExporting(true);
    try {
      await exportSetlist(playlistName, tracks);
    } catch (e) {
      alert("Export failed: " + (e instanceof Error ? e.message : "Unknown error"));
    } finally {
      setExporting(false);
    }
  }

  if (loading) {
    return (
      <div className="setlist-panel">
        <div className="empty-state">
          <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} />
          <p>Claude is crafting your setlist…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="setlist-panel">
        <div className="empty-state">
          <div className="icon">!</div>
          <p style={{ color: "var(--red)" }}>{error}</p>
        </div>
      </div>
    );
  }

  if (!tracks.length) {
    return (
      <div className="setlist-panel">
        <div className="empty-state">
          <div className="icon">♫</div>
          <p>Configure your event on the left and hit Generate Setlist to get started.</p>
        </div>
      </div>
    );
  }

  const unvettedCount = tracks.filter((t) => !t.vetted).length;

  return (
    <div className="setlist-panel">
      {/* Header */}
      <div className="setlist-header">
        <p className="panel-title">
          Generated Setlist — {tracks.length} tracks
          {unvettedCount > 0 && (
            <span className="unvetted-badge" style={{ marginLeft: 8 }}>
              {unvettedCount} unvetted
            </span>
          )}
        </p>
        <button
          className="btn btn-outline"
          style={{ marginLeft: "auto", fontSize: 11, padding: "4px 10px" }}
          onClick={() => setShowReasons((r) => !r)}
        >
          {showReasons ? "Hide" : "Show"} AI reasoning
        </button>
      </div>

      {/* Arc description */}
      {result?.arc_description && (
        <div className="arc-card">{result.arc_description}</div>
      )}

      {/* Track list (draggable) */}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={tracks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
          <div className="track-list">
            {tracks.map((track, i) => (
              <TrackRow key={track.id} track={track} index={i} showReasons={showReasons} />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {/* Export bar */}
      <div className="export-bar">
        <input
          type="text"
          value={playlistName}
          onChange={(e) => setPlaylistName(e.target.value)}
          placeholder="Playlist name"
        />
        <button
          className="btn btn-primary"
          style={{ width: "auto" }}
          onClick={handleExport}
          disabled={exporting}
        >
          {exporting ? "Exporting…" : "Export to rekordbox XML"}
        </button>
      </div>
    </div>
  );
}
