# Hosting the live demo on Hetzner

Stands up the **operator console + brain** on one Hetzner VPS, behind **automatic HTTPS**, a
**single passcode**, and `noindex`, so the Vercel landing page's "Live demo" link works for
evaluators. The real field system still runs offline/local — this is only the demo shop window.

Architecture: `Caddy (443)` → passcode → `/brain/*` to the brain, everything else to the console.
One origin, so one passcode covers the console, the REST API, and the websocket.

## 0. Prereqs
- A domain you control (e.g. `triangletechno.com`) so you can add a DNS record.
- The repo reachable from the server (a private GitHub repo is easiest; you likely have one for
  Vercel already). Otherwise `scp` the folder up.

## 1. Create the server
1. Hetzner Cloud Console → **New Project** → **Add Server**.
2. Location: pick one near you. Image: **Ubuntu 24.04**.
3. Type: **CX22** (2 vCPU / 4 GB) — enough to build the Next.js console. (CPX21 also fine.)
4. Add your **SSH key**. Create the server. Note its **IPv4**.
5. (Optional) Attach a Hetzner **Firewall** allowing inbound TCP **22, 80, 443** only.

## 2. Point DNS at it
In your DNS provider, add an **A record**: `demo.triangletechno.com → <server IPv4>`.
Wait for it to resolve (`dig +short demo.triangletechno.com` should return the IP).

## 3. Install Docker on the server
```bash
ssh root@<server-ip>
curl -fsSL https://get.docker.com | sh
```

## 4. Get the code
```bash
# private repo:
git clone https://github.com/<you>/<repo>.git triangle && cd triangle/deploy/hetzner
# (or scp the repo up and cd into deploy/hetzner)
```

## 5. Configure
```bash
cp .env.example .env
# generate a strong token and a passcode hash:
openssl rand -hex 16                                   # -> paste as TRIANGLE_TOKEN
docker run --rm caddy:2 caddy hash-password --plaintext 'CHOOSE-A-PASSCODE'   # -> BASIC_AUTH_HASH
nano .env    # set DOMAIN, TRIANGLE_TOKEN, BASIC_AUTH_USER, BASIC_AUTH_HASH
```

## 6. Launch
```bash
docker compose -f docker-compose.prod.yml up -d --build      # brain + console + HTTPS
# optional: a populated, MOVING picture (honest, labeled bench signal):
docker compose -f docker-compose.prod.yml --profile demo up -d
```
Caddy fetches a Let's Encrypt certificate automatically on first hit (needs ports 80+443 open and
DNS resolving). Give it ~30 s, then open **https://demo.triangletechno.com** — you'll get the
passcode prompt, then the console. With the `demo` profile on, you'll see a moving track + alert
under a **"BENCH TEST SIGNAL"** banner.

## 7. Wire the landing page to it
In Vercel → your landing project → **Settings → Environment Variables**:
```
NEXT_PUBLIC_DEMO_URL = https://demo.triangletechno.com
```
Redeploy the landing. Its "Live demo" links now open the hosted console.

## Operate
```bash
docker compose -f docker-compose.prod.yml logs -f          # tail logs
docker compose -f docker-compose.prod.yml --profile demo down   # stop the bench signal
docker compose -f docker-compose.prod.yml down             # stop everything
docker compose -f docker-compose.prod.yml up -d --build    # after a git pull, redeploy
```

## Notes / honesty
- This is a **demo**, not the field system. Anything shown while the `demo` profile runs is a
  clearly-labeled bench signal (synthetic audio through the real detector), never a live field
  detection. Turn the profile off and the console shows the honest empty state.
- The passcode + `noindex` are the guardrail for a hosted operator UI. Change the passcode before
  sharing; rotate `TRIANGLE_TOKEN` if it leaks.
- Cost is a few euros/month for a CX22.
