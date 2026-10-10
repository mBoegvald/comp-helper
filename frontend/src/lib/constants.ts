import type { Role } from "./types.ts";

export const ROLES: Role[] = ["top", "jungle", "mid", "bot", "support"];
export const ROLE_LABEL: Record<Role, string> = {
  top: "Top",
  jungle: "Jungle",
  mid: "Mid",
  bot: "Bot",
  support: "Support",
};
export const ROLE_SHORT: Record<Role, string> = { top: "TOP", jungle: "JG", mid: "MID", bot: "BOT", support: "SUP" };

export const DIFF_HELP =
  "Win rate compared with what these two champions usually win. Favored is +2 or more, Unfavored is -2 or less. " +
  "A champion with a low overall win rate can be Favored at 49%.";
export const LOW_SAMPLE_HELP = "Fewer than 200 games: the picker trusts it at 70%";

export interface Stage {
  id: string;
  title: string;
  desc: string;
  confirm?: string; // asked before starting
}

export const STAGES: Stage[] = [
  {
    id: "lolalytics",
    title: "Refresh win rates",
    desc: "All roles from Lolalytics. About 5 minutes. Do this after each patch.",
  },
  {
    id: "reddit",
    title: "Fetch missing Reddit",
    desc: "Only champions without Reddit data. One request per minute, so new champions take 2 to 4 minutes each.",
  },
  { id: "tips", title: "Rebuild tips", desc: "Re-extract matchup tips from the downloaded Reddit threads. Seconds." },
  {
    id: "comments",
    title: "Fetch Reddit comments",
    desc: "Replies to the best threads per champion. Many hours, run it overnight.",
    confirm: "This takes many hours at one Reddit request per minute. Start it?",
  },
  { id: "all", title: "Everything", desc: "Win rates, then missing Reddit, then tips." },
];

// what the edit API accepts
export const CURATED_RESULTS = ["Favored", "Even", "Even / skill", "Unfavored"];
export const BLIND_OPTIONS = ["Yes", "Mostly", "No"];
