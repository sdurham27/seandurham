-- Migration 003 — Remove Spotify columns, SoundCloud is the sole enrichment source
--
-- Safe to run whether or not you ran 002 (all operations use IF EXISTS).
-- If you haven't run 002 yet, skip it and run this one instead.

-- Drop the view first — it depends on Spotify columns and must be removed
-- before we can drop those columns from the table
drop view if exists enriched_tracks;

-- Ensure SoundCloud columns exist (idempotent if 002 already ran)
alter table track_features
  add column if not exists soundcloud_id      text,
  add column if not exists soundcloud_matched boolean;

-- Drop Spotify-specific columns — they'll never be populated
alter table track_features
  drop column if exists spotify_id,
  drop column if exists matched,
  drop column if exists valence,
  drop column if exists energy,
  drop column if exists danceability,
  drop column if exists acousticness,
  drop column if exists instrumentalness,
  drop column if exists tempo;

create index if not exists track_features_sc_id_idx
  on track_features(soundcloud_id);

-- Rebuild the view without Spotify columns
create view enriched_tracks as
select
  t.*,
  tf.soundcloud_id,
  tf.soundcloud_matched,
  coalesce(tf.soundcloud_matched, false) as pipeline_vetted,
  tv.vibe_tags,
  tv.energy_level,
  tv.mood,
  tv.best_for,
  tv.vetted
from tracks t
left join track_features tf on tf.track_id = t.id
left join track_vibes    tv on tv.track_id = t.id;
