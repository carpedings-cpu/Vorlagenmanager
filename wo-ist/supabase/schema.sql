-- Wo ist's? · Autorin: Diana Ziegler
-- Gemeinsamer Haushalt: beide Geräte melden sich mit demselben Konto an.
-- Jede Zeile gehört dem Konto, das sie angelegt hat (haushalt = auth.uid()).
-- Projekt: wo-ist (uvvqgwbshdtwlveopgvn), Region eu-central-1.

create table if not exists public.eintraege (
  id text primary key,
  haushalt uuid not null default auth.uid() references auth.users (id) on delete cascade,
  gegenstand text not null default '',
  ort text not null default '',
  originalsatz text not null default '',
  foto_pfad text,
  erstellt timestamptz not null default now(),
  verlauf jsonb not null default '[]'::jsonb,
  geaendert timestamptz not null default now(),
  geloescht boolean not null default false,
  server_zeit timestamptz not null default now()  -- Eingang beim Server, wird von der App nicht ausgewertet
);

create index if not exists eintraege_haushalt on public.eintraege (haushalt);

alter table public.eintraege enable row level security;

create policy "Haushalt liest eigene Einträge" on public.eintraege
  for select to authenticated using (haushalt = (select auth.uid()));
create policy "Haushalt legt eigene Einträge an" on public.eintraege
  for insert to authenticated with check (haushalt = (select auth.uid()));
create policy "Haushalt ändert eigene Einträge" on public.eintraege
  for update to authenticated using (haushalt = (select auth.uid())) with check (haushalt = (select auth.uid()));
create policy "Haushalt löscht eigene Einträge" on public.eintraege
  for delete to authenticated using (haushalt = (select auth.uid()));

insert into storage.buckets (id, name, public)
values ('fotos', 'fotos', false)
on conflict (id) do nothing;

create policy "Haushalt liest eigene Fotos" on storage.objects
  for select to authenticated
  using (bucket_id = 'fotos' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "Haushalt lädt eigene Fotos hoch" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'fotos' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "Haushalt ersetzt eigene Fotos" on storage.objects
  for update to authenticated
  using (bucket_id = 'fotos' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "Haushalt löscht eigene Fotos" on storage.objects
  for delete to authenticated
  using (bucket_id = 'fotos' and (storage.foldername(name))[1] = (select auth.uid())::text);
