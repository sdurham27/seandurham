-- DJ Setlist AI — Initial Schema
-- Run this in your Supabase SQL editor

-- ============================================================
-- tracks
-- ============================================================
create table if not exists tracks (
  id          uuid primary key default gen_random_uuid(),
  source_id   text unique,           -- rekordbox internal ID
  title       text not null,
  artist      text not null default '',
  album       text not null default '',
  genre       text not null default '',
  bpm         numeric(6,2),
  camelot_key text,                  -- e.g. "8A", "12B"
  play_count  integer not null default 0,
  date_added  date,
  rating      integer not null default 0,  -- 0–5 stars
  file_path   text not null default '',
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

create index if not exists tracks_genre_idx on tracks(genre);
create index if not exists tracks_bpm_idx   on tracks(bpm);
create index if not exists tracks_key_idx   on tracks(camelot_key);

-- auto-update updated_at
create or replace function update_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists tracks_updated_at on tracks;
create trigger tracks_updated_at
  before update on tracks
  for each row execute function update_updated_at();

-- ============================================================
-- track_features  (Spotify audio features)
-- ============================================================
create table if not exists track_features (
  id                  uuid primary key default gen_random_uuid(),
  track_id            uuid not null references tracks(id) on delete cascade,
  spotify_id          text,
  matched             boolean not null default false,
  valence             numeric(5,4),   -- 0.0–1.0
  energy              numeric(5,4),
  danceability        numeric(5,4),
  acousticness        numeric(5,4),
  instrumentalness    numeric(5,4),
  tempo               numeric(6,2),
  created_at          timestamptz default now()
);

create unique index if not exists track_features_track_id_idx on track_features(track_id);
create index if not exists track_features_spotify_id_idx on track_features(spotify_id);

-- ============================================================
-- track_vibes  (AI-generated vibe tags)
-- ============================================================
create table if not exists track_vibes (
  id           uuid primary key default gen_random_uuid(),
  track_id     uuid not null references tracks(id) on delete cascade,
  vibe_tags    text[]  not null default '{}',
  energy_level integer not null default 5 check (energy_level between 1 and 10),
  mood         text    not null default '',
  best_for     text[]  not null default '{}',
  vetted       boolean not null default false,
  created_at   timestamptz default now()
);

create unique index if not exists track_vibes_track_id_idx on track_vibes(track_id);
create index if not exists track_vibes_energy_idx  on track_vibes(energy_level);
create index if not exists track_vibes_vetted_idx  on track_vibes(vetted);

-- GIN indexes for array search (e.g. WHERE 'dark' = ANY(vibe_tags))
create index if not exists track_vibes_tags_gin    on track_vibes using gin(vibe_tags);
create index if not exists track_vibes_bestfor_gin on track_vibes using gin(best_for);

-- ============================================================
-- Convenience view: enriched_tracks
-- ============================================================
create or replace view enriched_tracks as
select
  t.*,
  tf.spotify_id,
  tf.matched as spotify_matched,
  tf.valence,
  tf.energy        as spotify_energy,
  tf.danceability,
  tf.acousticness,
  tf.instrumentalness,
  tf.tempo         as spotify_tempo,
  tv.vibe_tags,
  tv.energy_level,
  tv.mood,
  tv.best_for,
  tv.vetted
from tracks t
left join track_features tf on tf.track_id = t.id
left join track_vibes    tv on tv.track_id = t.id;
