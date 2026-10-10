// One function per endpoint of webapp.py. Errors come back as {error} with a 4xx/5xx status.
import type {
  Accounts,
  ChampionLookup,
  DraftRequest,
  CuratedChampion,
  CuratedField,
  Matchup,
  Me,
  Meta,
  Ok,
  Recommendation,
  Role,
  Status,
  Suggestion,
  Suggestions,
} from "./types.ts";

async function request<T>(path: string, body?: object): Promise<T> {
  const init: RequestInit = body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : {};
  const r = await fetch(path, init);
  const data = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
  if (!r.ok || data.error) throw new Error(data.error || `HTTP ${r.status}`);
  return data as T;
}

/** The message of anything a `catch` receives. */
export const errorMessage = (e: unknown): string => (e instanceof Error ? e.message : String(e));

const q = (params: Record<string, string>) => new URLSearchParams(params).toString();

export const getMeta = () => request<Meta>("/api/meta");
export const recommend = (draft: DraftRequest) => request<Recommendation>("/api/recommend", draft);
export const getChampion = (role: Role, name: string) => request<ChampionLookup>(`/api/champion?${q({ role, name })}`);
export const getMatchup = (role: Role, a: string, b: string) => request<Matchup>(`/api/matchup?${q({ role, a, b })}`);
export const getStatus = () => request<Status>("/api/status");
export const startUpdate = (stage: string) => request<Ok>("/api/update", { stage });
export const stopUpdate = () => request<Ok>("/api/stop", {});

export const getCuratedChampion = (role: Role, name: string) =>
  request<CuratedChampion>(`/api/curated/champion?${q({ role, name })}`);
export const saveCuratedChampion = (role: Role, champion: string, fields: Partial<Record<CuratedField, string>>) =>
  request<CuratedChampion>("/api/curated/champion", { role, champion, fields });
export const saveCuratedMatchup = (role: Role, champion: string, opponent: string, result: string, tip: string) =>
  request<Matchup>("/api/curated/matchup", { role, champion, opponent, result, tip });

export const getMe = () => request<Me>("/api/me");
export const signUp = (username: string, password: string) => request<Me>("/api/signup", { username, password });
export const signIn = (username: string, password: string) => request<Me>("/api/login", { username, password });
export const signOut = () => request<Me>("/api/logout", {});
export const getAccounts = () => request<Accounts>("/api/admin/accounts");
export const setBlocked = (id: number, blocked: boolean) => request<Accounts>("/api/admin/block", { id, blocked });

export const suggestNote = (role: Role, champion: string, opponent: string | null, text: string, source: string) =>
  request<{ note: Suggestion }>("/api/notes", { role, champion, opponent, text, source });
export const getMyNotes = () => request<Suggestions>("/api/notes/mine");
export const getReviewQueue = () => request<Suggestions>("/api/admin/review");
export const reviewNote = (id: number, approve: boolean, text?: string, note?: string) =>
  request<Suggestions>("/api/admin/review", { id, approve, text, note });
export const deleteNote = (id: number) => request<Ok>("/api/admin/notes/delete", { id });
export const promoteNote = (id: number) => request<Matchup>("/api/admin/notes/promote", { id });
