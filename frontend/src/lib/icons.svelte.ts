// Champion icons come from Riot's public image server; until its version is known (or offline) icons show initials.
const ICON_ID: Record<string, string> = {
  Wukong: "MonkeyKing",
  "Nunu & Willump": "Nunu",
  "Renata Glasc": "Renata",
  "Kai'Sa": "Kaisa",
  "Kha'Zix": "Khazix",
  "Cho'Gath": "Chogath",
  "Vel'Koz": "Velkoz",
  "Bel'Veth": "Belveth",
  LeBlanc: "Leblanc",
  "K'Sante": "KSante",
  "Dr. Mundo": "DrMundo",
};

export const icons = $state({ version: null as string | null });

fetch("https://ddragon.leagueoflegends.com/api/versions.json")
  .then((r) => r.json())
  .then((v: string[]) => (icons.version = v[0]))
  .catch(() => {});

export function iconUrl(name: string) {
  if (!icons.version) return null;
  const id = ICON_ID[name] || name.replace(/[^A-Za-z]/g, "");
  return `https://ddragon.leagueoflegends.com/cdn/${icons.version}/img/champion/${id}.png`;
}
