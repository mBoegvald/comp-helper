// The JSON webapp.py sends, one type per answer. Keep in step with the api_* functions there.

export type Role = "top" | "jungle" | "mid" | "bot" | "support";
export type Label = "Favored" | "Even" | "Unfavored";
export type Need = "ap" | "ad";

/** A champion's notes for a role (hand edits, else role_data.py defaults). */
export interface Champion {
  name: string;
  arch: string | null;
  dmg: string | null;
  comps: string | null;
  good: string | null;
  bad: string | null;
  when: string | null;
  blind: string | null;
}

export interface RoleInfo {
  id: Role;
  champions: string[];
  matchups: number;
  updated: number | null; // seconds since 1970
}

/** /api/meta */
export interface Meta {
  roles: RoleInfo[];
  names: string[];
  styles: string[];
  patch: string;
  reddit_champions: number;
  tips_updated: number | null;
}

export interface LaneNote {
  from: "notes";
  who: string;
  text: string;
}

export interface RedditSnippet {
  text: string;
  date: string;
  url: string;
}

export interface RedditGroup {
  who: string;
  mentions: number;
  newest: string;
  tips: RedditSnippet[];
}

/** /api/matchup: everything about champ vs opp in one role, from champ's side. */
export interface Matchup {
  champ: string;
  opp: string;
  score: number | null;
  wr?: number;
  dnorm?: number;
  games?: number;
  label: Label | null;
  low_sample: boolean;
  hand_result: string | null;
  mismatch: boolean;
  tips: LaneNote[];
  reddit: RedditGroup[];
  community: CommunityNote[]; // approved, from both sides (`who`)
}

/** One reason in a pick's score. */
export interface Part {
  kind: "matchup" | "text" | "archetype" | "style" | "damage" | "blind";
  value: number;
  enemy?: string;
  enemy_name?: string;
  main?: boolean;
  text?: string;
  wr?: number;
  dnorm?: number;
  games?: number;
  label?: Label | null;
  low_sample?: boolean;
}

export interface Pick extends Champion {
  key: string;
  score: number;
  parts: Part[];
  lane?: Matchup | null;
}

/** How /api/recommend read a typed name in one slot. */
export interface Slot {
  name: string | null;
  known: boolean;
  in_role: boolean;
}

/** /api/recommend */
export interface Recommendation {
  role: Role;
  enemy_main: string | null;
  need: Need | null;
  need_detected: Need | null;
  style: string | null;
  slots: Record<string, Slot>; // "ally.top", "enemy.mid", ...
  picks: Pick[];
  avoid: Pick[];
  candidates: number;
}

export interface DraftRequest {
  role: Role;
  ally: Partial<Record<Role, string>>;
  enemy: Partial<Record<Role, string>>;
  style: string;
  need: string;
  unavailable: string[];
  top: number;
}

export interface MatchupRow {
  opp: string;
  score: number | null;
  wr: number | null;
  dnorm: number | null;
  games: number | null;
  label: Label | null;
  low_sample: boolean;
  notes: number;
  reddit: number;
}

/** /api/champion: every matchup of one champion in one role. */
export interface ChampionLookup {
  role: Role;
  champion: Champion;
  in_role: boolean;
  matchups: MatchupRow[];
  community: CommunityNote[]; // approved notes about the champion itself
}

/** /api/status */
export interface Status {
  running: boolean;
  log: string;
}

export type HandField = "archetype" | "damage" | "comps" | "good_into" | "struggles_into" | "pick_when" | "blind_safe";

/** /api/hand/champion: a champion's hand edits and the defaults they override. */
export interface HandChampion {
  role: Role;
  champion: string;
  hand: Record<HandField, string | null>;
  defaults: Record<HandField, string>;
  archetypes: string[];
  updated_at: string | null;
}

export interface Ok {
  ok: boolean;
  error?: string;
}

/** A signed-in account (hosted mode). In local mode the server answers as the admin "you". */
export interface User {
  id: number | null;
  username: string;
  role: "contributor" | "admin";
}

/** /api/me, /api/login, /api/signup, /api/logout */
export interface Me {
  hosted: boolean;
  user: User | null;
  admin: boolean;
}

export interface Account {
  id: number;
  username: string;
  role: "contributor" | "admin";
  blocked: 0 | 1;
  created_at: string;
}

/** /api/admin/accounts, /api/admin/block */
export interface Accounts {
  accounts: Account[];
}

export type NoteStatus = "pending" | "approved" | "rejected";

/** An approved community note as the page shows it. `who` is the side a matchup note was written from. */
export interface CommunityNote {
  id: number;
  author: string | null;
  text: string;
  source: string | null;
  approved_at: string | null;
  who?: string;
}

/** A note as its author or the reviewing admin sees it. No opponent: a note about the champion itself. */
export interface Suggestion {
  id: number;
  role: Role;
  champion: string;
  opponent: string | null;
  text: string;
  source: string | null;
  status: NoteStatus;
  author: string | null;
  created_at: string;
  reviewed_at: string | null;
  review_note: string | null;
}

/** /api/notes/mine, /api/admin/review */
export interface Suggestions {
  notes: Suggestion[];
}
