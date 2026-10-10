<script lang="ts">
  import { session } from "../../lib/session.svelte.ts";
</script>

<div class="privacy panel">
  <h2>Privacy</h2>
  <p>
    This site helps you pick League of Legends champions. It keeps as little about you as it can. This page says what,
    why and for how long.
  </p>

  <h3>Who runs it</h3>
  <p>
    {#if session.contact}
      You can reach the person who runs this site at <b>{session.contact}</b>.
    {:else}
      The site is run by its admin; ask them for a contact address.
    {/if}
  </p>

  <h3>If you have an account</h3>
  <ul>
    <li>
      Your <b>username</b>, and your <b>password</b> stored as a scrypt hash, which cannot be turned back into the password.
    </li>
    <li>
      The <b>notes</b> you suggest, their review status, and the admin's reason if a note or edit was not accepted.
    </li>
    <li>
      A <b>sign-in cookie</b> that keeps you signed in for up to 30 days. It is only for signing in: there are no tracking
      or advertising cookies.
    </li>
  </ul>

  <h3>For every visitor</h3>
  <ul>
    <li>
      The <b>address (IP)</b> of each sign-in and sign-up attempt, kept for at most 24 hours, to stop password guessing and
      spam accounts.
    </li>
    <li>The draft you type is sent to the server to work out picks, and not stored.</li>
    <li>Your draft and settings are remembered in your own browser only.</li>
    <li>If something breaks, the server keeps a log of that error.</li>
  </ul>

  <h3>Who else sees what</h3>
  <ul>
    <li>Your username is shown next to your approved notes, and as “(from your name)” on a lane tip made from one.</li>
    <li>The admin sees accounts and notes, to review them and stop abuse.</li>
    <li>
      Champion icons come from Riot Games' image server (ddragon.leagueoflegends.com), which sees your address like any
      website you load images from.
    </li>
  </ul>

  <h3>How long</h3>
  <p>
    Your account and notes stay until you delete them. Sign-in attempts are kept for 24 hours. Copies of the database
    are kept as backups for up to 14 days, so deleted data is gone from those within that time.
  </p>

  <h3>What you can do</h3>
  <ul>
    <li>
      Edit or withdraw your notes, and delete your account, under <b>My account</b>. Deleting removes your notes and the
      credit on lane tips too.
    </li>
    <li>Ask the contact above for a copy of what the site holds about you, or to correct it.</li>
  </ul>
</div>

<style>
  .privacy {
    max-width: 760px;
    line-height: 1.55;
  }
  h3 {
    font-size: 14px;
    margin: 16px 0 4px;
  }
  p,
  ul {
    margin: 4px 0;
  }
  ul {
    padding-left: 20px;
  }
</style>
