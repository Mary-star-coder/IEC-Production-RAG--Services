create table if not exists public.documents (
    document_id uuid primary key,
    owner_user_id uuid not null references auth.users (id) on delete cascade,
    filename text not null,
    file_hash text not null,
    file_size bigint not null check (file_size > 0),
    chunk_count integer not null check (chunk_count > 0),
    file_type text not null,
    created_at timestamptz not null default now(),
    unique (owner_user_id, file_hash)
);

alter table public.documents enable row level security;

grant select, insert, delete on public.documents to authenticated;

drop policy if exists "Users manage their own documents" on public.documents;
create policy "Users manage their own documents"
    on public.documents
    for all
    to authenticated
    using ((select auth.uid()) = owner_user_id)
    with check ((select auth.uid()) = owner_user_id);

create table if not exists public.question_cache (
    user_id uuid not null references auth.users (id) on delete cascade,
    question_hash text not null check (question_hash ~ '^[0-9a-f]{64}$'),
    top_k integer not null check (top_k between 1 and 10),
    response jsonb not null,
    created_at timestamptz not null default now(),
    primary key (user_id, question_hash, top_k)
);

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

alter table public.question_cache enable row level security;

grant select, insert, update, delete on public.question_cache to authenticated;

drop policy if exists "Users manage their own question cache"
    on public.question_cache;
create policy "Users manage their own question cache"
    on public.question_cache
    for all
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create or replace function public.clear_question_cache_after_document_change()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    if tg_op = 'DELETE' then
        delete from public.question_cache
        where user_id = old.owner_user_id;
        return old;
    end if;

    delete from public.question_cache
    where user_id = new.owner_user_id;
    return new;
end;
$$;

revoke all on function public.clear_question_cache_after_document_change()
    from public, anon, authenticated;

drop trigger if exists clear_question_cache_after_document_insert
    on public.documents;
create trigger clear_question_cache_after_document_insert
    after insert on public.documents
    for each row
    execute function public.clear_question_cache_after_document_change();

drop trigger if exists clear_question_cache_after_document_delete
    on public.documents;
create trigger clear_question_cache_after_document_delete
    after delete on public.documents
    for each row
    execute function public.clear_question_cache_after_document_change();

insert into storage.buckets (id, name, public)
values ('documents', 'documents', false)
on conflict (id) do update set public = false;

drop policy if exists "Users read their own document files" on storage.objects;
create policy "Users read their own document files"
    on storage.objects
    for select
    to authenticated
    using (
        bucket_id = 'documents'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );

drop policy if exists "Users upload their own document files" on storage.objects;
create policy "Users upload their own document files"
    on storage.objects
    for insert
    to authenticated
    with check (
        bucket_id = 'documents'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );

drop policy if exists "Users delete their own document files" on storage.objects;
create policy "Users delete their own document files"
    on storage.objects
    for delete
    to authenticated
    using (
        bucket_id = 'documents'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );
