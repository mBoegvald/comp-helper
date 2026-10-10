// The admin's review queue: the Admin tab lists it, the tab shows how many notes wait.
import { dataChanged } from "./app.svelte.ts";
import { errorMessage, getReviewQueue, reviewNote } from "./api.ts";
import type { Suggestion } from "./types.ts";

export const review = $state({ notes: [] as Suggestion[], error: null as string | null });

export async function loadReview() {
  try {
    review.notes = (await getReviewQueue()).notes;
    review.error = null;
  } catch (e) {
    review.error = errorMessage(e);
  }
}

/** Approve (with the admin's text) or reject (with an optional reason) one waiting note. */
export async function decide(id: number, approve: boolean, text?: string, reason?: string) {
  try {
    review.notes = (await reviewNote(id, approve, text, reason)).notes;
    review.error = null;
    if (approve) dataChanged(); // the note now shows on the page
  } catch (e) {
    review.error = errorMessage(e);
  }
}
