import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { SetlistTrack } from "../lib/api";
import { EnergyBar } from "./EnergyBar";

interface Props {
  track: SetlistTrack;
  index: number;
  showReasons: boolean;
}

export function TrackRow({ track, index, showReasons }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: track.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`track-row${!track.vetted ? " unvetted" : ""}${isDragging ? " dragging" : ""}`}
    >
      <span className="track-num">{index + 1}</span>

      <div className="track-info">
        <div className="track-title">
          {!track.vetted && <span className="unvetted-badge">NEW</span>}{" "}
          {track.title}
        </div>
        <div className="track-artist">{track.artist}</div>
        <div className="track-tags">
          {track.mood && <span className="tag mood">{track.mood}</span>}
          {track.vibe_tags.slice(0, 3).map((t) => (
            <span key={t} className="tag">{t}</span>
          ))}
        </div>
      </div>

      <EnergyBar level={track.energy_level} />

      <div className="track-key">{track.camelot_key ?? "—"}</div>

      <div className="track-bpm">
        {track.bpm ? `${track.bpm.toFixed(0)}` : "—"}
        <div style={{ fontSize: 10, color: "var(--text-dim)" }}>BPM</div>
      </div>

      {showReasons && track.reason && (
        <div className="track-reason">{track.reason}</div>
      )}
    </div>
  );
}
