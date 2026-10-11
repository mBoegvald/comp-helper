# Hosting Pick Helper

This runs the site for everyone: anyone can read the picks, people with an account suggest notes, and you review
them as admin. It is the app in hosted mode with Caddy in front for HTTPS, both in Docker. The Windows app is not
affected; it keeps running locally without accounts.

You need a server (here: Hetzner Cloud) and a domain or subdomain you can point at it, e.g. `picks.example.com`.

## 1. Create the server

1. In the Hetzner Cloud console, create a server: type **CX22** (2 vCPU, 4 GB) is plenty, image **Ubuntu 24.04**,
   and add your SSH key.
2. Create a **firewall** for it that allows incoming **22** (SSH), **80** and **443** (TCP), and **443 UDP**
   (HTTP/3). Nothing else is needed: the app itself is only reachable through Caddy.
3. Note the server's IPv4 (and IPv6) address.

## 2. Point your domain at it

At your DNS provider, add an **A** record for `picks.example.com` with the IPv4 address (and an **AAAA** record with
the IPv6 address). Wait until `ping picks.example.com` answers from the server's address. Caddy needs this to get the
HTTPS certificate.

## 3. Install Docker

SSH in as root, then:

```
curl -fsSL https://get.docker.com | sh
```

(Docker's own install script; it also installs `docker compose`.)

## 4. Get the app and start it

```
git clone https://github.com/mBoegvald/comp-helper.git pickhelper
cd pickhelper
cp .env.example .env
nano .env                      # set DOMAIN=picks.example.com (your domain) and CONTACT (your email)
docker compose up -d --build
docker compose ps              # app should show "healthy" within a minute
```

Open `https://picks.example.com`. The first start copies the database and Reddit downloads from the repo into the
`data` volume; later starts never overwrite them.

## 5. Create your admin account

```
docker compose exec app python manage.py create-admin yourname
```

It asks for the password (at least 10 characters). Sign in on the site: you get the Admin tab (review queue and
accounts), the Data tab's update buttons, and Edit on champions and matchups.

## 6. Update the data

As admin, use the **Data** tab: **Refresh win rates** after each patch, **Fetch missing Reddit** when champions are
added. Or from the server:

```
docker compose exec app python update.py lolalytics
```

To refresh the win rates every week without thinking about it, add to root's crontab (`crontab -e`); this runs on
Thursday at 05:00, after Wednesday's patches, and its progress goes to `logs/update.log` as usual:

```
0 5 * * 4 cd /root/pickhelper && docker compose exec -T app python update.py lolalytics >/dev/null 2>&1
```

## Updating the app

```
cd pickhelper
git pull
docker compose up -d --build
```

Accounts, notes and data live in the `data` volume and are kept.

## Backups

Every data update already keeps a daily copy in the volume (`data/backups`, the last 14). For your own backups, make
a consistent copy (safe while the site runs) and fetch it to the server's disk:

```
docker compose exec app python manage.py backup data/backups/manual-$(date +%F).db
docker compose cp app:/app/data/backups/manual-$(date +%F).db ./
```

To do this every night, create the folder once (`mkdir -p /root/backups`), then add to root's crontab
(`crontab -e`):

```
30 4 * * * cd /root/pickhelper && docker compose exec -T app python manage.py backup data/backups/nightly-$(date +\%F).db && docker compose cp app:/app/data/backups/nightly-$(date +\%F).db /root/backups/ && docker compose exec -T app rm data/backups/nightly-$(date +\%F).db && find /root/backups -name 'nightly-*.db' -mtime +13 -delete
```

and copy `/root/backups` off the server now and then (e.g. with `scp`), or enable Hetzner's server backups.

To copy them off every night instead, rent a Hetzner Storage Box (the smallest is plenty), add the server's SSH key
to it, and add a second crontab line. `--delete` keeps the copy the same 14 days as the server:

```
45 4 * * * rsync -a --delete -e 'ssh -p 23' /root/backups/ u12345@u12345.your-storagebox.de:pickhelper/
```

Keep backups for at most 14 days, wherever they are: the privacy page promises that deleted accounts are gone from
backups within that time. Delete manual copies when you are done with them.

## Privacy and deleting accounts

The site has a Privacy page (footer link) that says what is stored and for how long, with `CONTACT` from `.env` as
the address to write to. Signed-in people delete their own account under **My account** (their password confirms
it); their notes go with it, and their name is taken off lane tips made from their notes. If someone asks you
instead:

```
docker compose exec app python manage.py delete-account theirname
```

It asks for the name again before deleting. The last admin account cannot be deleted. A restored backup brings deleted
accounts back, so delete them again after restoring.

## Restoring a backup

```
docker compose stop app
docker compose cp ./manual-2026-10-10.db app:/app/data/pickhelper.db
docker compose start app
```

## Logs and trouble

- **Someone forgot their password**: Admin tab, **Reset password** on their row. Pass on the new password it shows;
  they can change it under My account.
- `docker compose logs app` shows the app, including tracebacks of server errors (visitors only see a plain message).
- `docker compose exec app tail -50 logs/update.log` shows the last data update. The log trims itself to its newest
  part past 2 MB, and Docker keeps at most 30 MB of logs per service, so neither fills the disk.
- **"This server does not answer for that address"**: `DOMAIN` in `.env` does not match the address in the browser.
  Fix it and run `docker compose up -d`.
- **No HTTPS / certificate errors**: the domain does not point at the server yet, or port 80 or 443 is blocked;
  `docker compose logs caddy` says which.

## What protects the site

- Only Caddy is reachable from outside, over HTTPS with automatic certificates. The app port is private.
- The app answers only for your domain (`DOMAIN`), takes the visitor's address from Caddy for its rate limits
  (sign-in 10 per 15 min, sign-up 3 per hour per address), and runs as a non-root user.
- Passwords are hashed with scrypt; sessions are HttpOnly, Secure, SameSite cookies; every change must come from the
  site itself as JSON; the page has a Content-Security-Policy.
- New notes wait for your review; at most 20 per account can wait at once, and blocking an account removes its
  waiting notes.
