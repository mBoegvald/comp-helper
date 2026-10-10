// Who is using the page. Local mode (the Windows app): no accounts, you are the admin.
// Hosted mode: signed out, a contributor, or an admin. The server checks every request; this only shapes the page.
import { getMe, signIn, signOut, signUp } from "./api.ts";
import type { Me, User } from "./types.ts";

export const session = $state({ loaded: false, hosted: false, user: null as User | null, admin: false });

function apply(me: Me) {
  Object.assign(session, { loaded: true, hosted: me.hosted, user: me.user, admin: me.admin });
}

export async function loadSession() {
  try {
    apply(await getMe());
  } catch {
    apply({ hosted: false, user: null, admin: false });
  }
}

export const register = async (username: string, password: string) => apply(await signUp(username, password));
export const login = async (username: string, password: string) => apply(await signIn(username, password));
export const logout = async () => apply(await signOut());
