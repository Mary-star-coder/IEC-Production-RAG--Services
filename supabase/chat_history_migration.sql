create table if not exists public.chat_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    title text not null default 'New chat',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (id, user_id)
);

create index if not exists chat_sessions_user_updated_at_idx
    on public.chat_sessions (user_id, updated_at desc);

alter table public.chat_sessions enable row level security;

grant select, insert, update, delete on public.chat_sessions to authenticated;

drop policy if exists "Users manage their own chat sessions"
    on public.chat_sessions;
create policy "Users manage their own chat sessions"
    on public.chat_sessions
    for all
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create table if not exists public.chat_turns (
    id uuid primary key default gen_random_uuid(),
    chat_id uuid not null,
    user_id uuid not null references auth.users (id) on delete cascade,
    question text not null,
    answer text not null,
    citations jsonb not null default '[]'::jsonb,
    retrieved_chunks jsonb not null default '[]'::jsonb,
    selected_document_ids jsonb,
    abstained boolean not null default false,
    created_at timestamptz not null default now(),
    foreign key (chat_id, user_id)
        references public.chat_sessions (id, user_id)
        on delete cascade
);

create index if not exists chat_turns_chat_created_at_idx
    on public.chat_turns (chat_id, created_at);

alter table public.chat_turns enable row level security;

grant select, insert, delete on public.chat_turns to authenticated;

drop policy if exists "Users manage their own chat turns"
    on public.chat_turns;
create policy "Users manage their own chat turns"
    on public.chat_turns
    for all
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);
