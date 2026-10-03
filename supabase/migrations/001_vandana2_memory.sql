create extension if not exists pgcrypto;

create table if not exists public.strategy_memory (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  index_name text, regime text, strategy text, strike numeric, side text,
  entry numeric, oi numeric, premium numeric, volume bigint, iv numeric,
  greeks jsonb, expiry text, day_time text, result text, confidence numeric, extra jsonb
);

create table if not exists public.trade_memory (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  strategy text, index_name text, side text, strike numeric, entry numeric,
  exit numeric, r numeric, result text, regime text, expiry text,
  strike_distance numeric, day_time text, is_expiry boolean default false, extra jsonb
);

create table if not exists public.ai_memory (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  session_key text not null, layer_id text, model text, prompt_hash text,
  response jsonb, agreement boolean, latency_ms integer
);

create index if not exists strategy_memory_lookup
  on public.strategy_memory(index_name, regime, strategy, created_at desc);
create index if not exists trade_memory_lookup
  on public.trade_memory(index_name, strategy, created_at desc);
create index if not exists ai_memory_lookup
  on public.ai_memory(session_key, created_at desc);

alter table public.strategy_memory enable row level security;
alter table public.trade_memory enable row level security;
alter table public.ai_memory enable row level security;
