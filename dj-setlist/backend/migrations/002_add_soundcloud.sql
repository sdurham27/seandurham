-- Migration 002 — Add SoundCloud fields to track_features
-- Run this in your Supabase SQL editor after 001_initial_schema.sql

alter table track_features
  add column if not exists soundcloud_id      text,
  add column if not exists soundcloud_matched boolean;

create index if not exists track_features_sc_id_idx
  on track_features(soundcloud_id);

-- Regenerate the enriched_tracks view to include the new columns
create or replace view enriched_tracks as
select
  t.*,
  tf.spotify_id,
  tf.matched           as spotify_matched,
  tf.soundcloud_id,
  tf.soundcloud_matched,
  -- vetted = identified by at least one service
  coalesce(tf.matched, false) or coalesce(tf.soundcloud_matched, false) as pipeline_vetted,
  tf.valence,
  tf.energy            as spotify_energy,
  tf.danceability,
  tf.acousticness,
  tf.instrumentalness,
  tf.tempo             as spotify_tempo,
  tv.vibe_tags,
  tv.energy_level,
  tv.mood,
  tv.best_for,
  tv.vetted
from tracks t
left join track_features tf on tf.track_id = t.id
left join track_vibes    tv on tv.track_id = t.id;
