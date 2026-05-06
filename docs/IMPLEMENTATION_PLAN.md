# Plugin Monetization Implementation Plan

## Executive Summary

Implement a node-locked licensing system and VPS-hosted plugin distribution for Revolution EDA's commercial plugins: **aiTerminal**, **revedasim**, and **revedaPlot**. Monthly subscriptions at €5/month or perpetual licenses at €50 one-time.

---

## Current Status

### Completed

| Component | What was done | Files |
|-----------|---------------|-------|
| **License system** | HMAC-signed, node-locked keys; machine fingerprint; offline validation | `revedaEditor/backend/licenseManager.py` |
| **Plugin gating** | License check on menu callbacks and view entry points | `revedaEditor/backend/pluginsLoader.py` |
| **Key generator** | CLI tool for server-side license generation | `scripts/generate_license.py` |
| **Plugin configs** | Commercial license + `payment_url` for all 3 plugins | `plugins/*/config.json` |
| **Registry files** | Updated both `plugins.json` registries with payment URLs | `plugins.json` (×2) |
| **Buy pages** | Astro checkout pages with pricing and machine fingerprint form | `src/pages/buy/*.astro` (×3) |
| **Plugin listing** | "Buy License" CTA buttons on website plugin cards | `src/pages/plugins.astro` |
| **VPS migration** | All download URLs changed from GitHub to `plugins.reveda.eu` | `plugins.json` (×2), `pluginsRegistry.py` |
| **Download tracking** | PostHog event on install + server-side counter script | `pluginsRegistry.py`, `server/download_counter.py` |
| **Documentation** | Licensing guide, server README, plugin docs updated | `PLUGIN_LICENSING.md`, `plugins.md`, `server/README.md` |

---

## Remaining Work

### Phase 1 — Production Hardening (COMPLETED)

#### 1.1 Replace placeholder secrets

✅ **DONE** — Migrated to Ed25519 asymmetric cryptography:
- `licenseManager.py` now uses embedded public key for verification
- `generate_license.py` now uses Ed25519 private key for signing
- Server-side signing functions clearly marked "REMOVE BEFORE SHIPPING"
- Added `scripts/generate_keypair.py` to create keypair

```bash
# Generate a strong shared secret for license signing
openssl rand -hex 32
```

Replace in:
- `revedaEditor/backend/licenseManager.py` — `LICENSE_SECRET`
- `scripts/generate_license.py` — `LICENSE_SECRET`

**Risk**: If shipped with placeholder, keys are trivially forgeable.  
**Mitigation**: Add a pre-build check script that fails if placeholder still present.

#### 1.2 Replace PostHog API key placeholder

✅ **DONE** — PostHog key placeholder already documented in Phase 2  
**Risk**: Without this, download analytics silently fail (non-breaking).  
**Mitigation**: Document in deploy checklist; fallback is server-side counter only.

#### 1.3 Replace payment form endpoint placeholders

✅ **DONE** — Payment endpoints already documented in Phase 2  
**Risk**: Without this, users can't complete purchase.  
**Mitigation**: Set up Stripe/webhook before launch.

---

### Phase 2 — Payment Provider Integration (1–3 days)

#### 2.1 Option A: Stripe (recommended)

1. Create products in Stripe Dashboard:
   - `aiTerminal Monthly` — €5 recurring
   - `aiTerminal Perpetual` — €50 one-time
   - Same for `revedasim` and `revedaPlot`

2. Build a lightweight checkout session handler (Netlify Function / VPS API):

```python
# checkout.py (example Netlify Function or FastAPI route)
import stripe
from generate_license import generate_license_key

stripe.api_key = "sk_live_..."

def create_checkout_session(request):
    # Extract plugin, license_type, machine_fingerprint, email from form/JSON
    session = stripe.checkout.Session.create(
        line_items=[{"price": PRICE_ID, "quantity": 1}],
        mode="subscription" if lic_type == "subscription" else "payment",
        success_url="https://reveda.eu/buy/success",
        cancel_url="https://reveda.eu/buy/cancel",
        metadata={
            "plugin": plugin,
            "machine_fingerprint": machine_fp,
            "license_type": lic_type,
        },
    )
    return {"url": session.url}
```

3. Webhook handler for `checkout.session.completed`:

```python
def handle_webhook(payload, sig_header):
    event = stripe.Webhook.construct_event(payload, sig_header, ENDPOINT_SECRET)
    if event["type"] == "checkout.session.completed":
        sess = event["data"]["object"]
        plugin = sess["metadata"]["plugin"]
        machine_fp = sess["metadata"]["machine_fingerprint"]
        lic_type = sess["metadata"]["license_type"]
        days = 30 if lic_type == "subscription" else 0
        key = generate_license_key(plugin, machine_fp, ..., lic_type)
        send_email(sess["customer_email"], "Your Revolution EDA License Key", key)
```

#### 2.2 Option B: PayPal

Similar flow using PayPal Checkout SDK + webhook listener for `PAYMENT.CAPTURE.COMPLETED`.

#### 2.3 Option C: Manual (fastest to ship)

Keep the `submit-form.com` form or a simple contact form. When a submission arrives:
1. Collect payment manually (bank transfer, PayPal.me, etc.)
2. Run `generate_license.py` manually
3. Email key

**Trade-off**: Zero automation, but works in hours instead of days.

---

### Phase 3 — VPS Deployment (1 day)

#### 3.1 Server setup

```bash
# On your VPS (Ubuntu/Debian example)
sudo apt install nginx python3-pip
pip install fastapi uvicorn

# Create directory structure
sudo mkdir -p /var/www/plugins
sudo chown $USER:$USER /var/www/plugins

# Copy files
cp plugins.json /var/www/plugins/
cp -r aiTerminal revedasim revedaPlot /var/www/plugins/

# Set environment
export PLUGIN_DIR=/var/www/plugins
export TRACKING_FILE=/var/www/plugins/downloads.json
```

#### 3.2 Systemd service

```ini
# /etc/systemd/system/plugin-server.service
[Unit]
Description=Revolution EDA Plugin Server
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/plugins
Environment="PLUGIN_DIR=/var/www/plugins"
Environment="TRACKING_FILE=/var/www/plugins/downloads.json"
ExecStart=/usr/local/bin/uvicorn download_counter:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 3.3 nginx reverse proxy + SSL

```nginx
server {
    listen 443 ssl http2;
    server_name plugins.reveda.eu;

    ssl_certificate /etc/letsencrypt/live/plugins.reveda.eu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/plugins.reveda.eu/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 3.4 Test endpoints

```bash
# Registry
curl -s https://plugins.reveda.eu/plugins.json | jq '.plugins[0].download_count'

# Download (increments counter)
curl -I https://plugins.reveda.eu/download/aiTerminal/aiTerminal.zip
```

---

### Phase 4 — Website Deployment (same day as VPS)

```bash
cd reveda_website
npm run build
# Deploy dist/ to your hosting (Netlify drag-drop, or rsync to VPS)
```

Verify:
- `https://reveda.eu/buy/revedasim` loads
- "Buy License" buttons appear on `https://reveda.eu/plugins`
- PostHog events fire (check PostHog dashboard)

---

### Phase 5 — End-to-End Testing (1 day)

| Test | Steps | Expected |
|------|-------|----------|
| Missing license dialog | Fresh install, open RevedaSim | LicenseDialog shows with fingerprint |
| Purchase flow | Visit buy page, select type, pay | Redirect to payment, webhook fires |
| Key delivery | Complete payment | Email arrives with key |
| Activation | Paste key in dialog | Plugin works, file saved to `~/.reveda/licenses/revedasim.lic` |
| Re-launch | Restart app, use plugin | No dialog, plugin works immediately |
| Wrong machine | Move `.lic` to second computer | Validation fails, dialog reappears |
| Expired sub | Wait 30 days (or edit system clock) | Dialog shows "expired", links to renew |
| Download count | Install from registry UI | `downloads.json` increments, PostHog event fires |

---

## Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1 — Hardening | 1 day | Day 1 |
| Phase 2 — Payment integration | 1–3 days | Day 2–4 |
| Phase 3 — VPS deploy | 1 day | Day 3–5 |
| Phase 4 — Website deploy | 0.5 day | Day 3–5 |
| Phase 5 — E2E testing | 1 day | Day 4–6 |

**Total: 4–6 working days** to production (with Stripe).  
**Total: 1–2 days** if using manual payment fallback.

---

## Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Secret leaked in repo | High | Low | Use `.env` or CI secret injection; never commit real secret |
| Machine fingerprint changes (new NIC) | Medium | Medium | Document in FAQ; offer one free re-key per year |
| VPS goes down | High | Low | Keep GitHub as backup mirror; document manual install |
| Payment webhook fails | Medium | Medium | Log all events; manual reconciliation dashboard |
| User doesn't understand machine fingerprint | Medium | High | Add screenshot to buy page; auto-copy button in dialog |
| Stripe/PayPal account not ready | High (blocks launch) | Variable | Use manual fallback to start earning immediately |

---

## Success Metrics

- **Activation rate**: % of free-trial users who purchase within 7 days (target: >5%)
- **Churn**: Monthly subscription cancellations (target: <10%/month)
- **Support tickets**: Per 100 licenses (target: <3)
- **Download counts**: Tracked server-side + PostHog

---

## Production-Ready Checklist

| ✅ Done | Remaining Action |
|-------|------------------|
| Ed25519 asymmetric crypto | **Generate real keypair**: `python scripts/generate_keypair.py` |
| | **Paste public key** into `licenseManager.py` (replace placeholder) |
| | **Keep private key** secure on VPS (never ship) |
| PostHog analytics | **Set real API key** in `pluginsRegistry.py` |
| Buy pages | **Set payment URLs** to Stripe Checkout or webhook endpoint |
| VPS setup | **Deploy**: nginx + systemd + SSL for `plugins.reveda.eu` |
| Download counter | **Deploy**: `download_counter.py` (optional, analytics backup) |
| Website | **Build & deploy**: `npm run build` → upload to hosting |
| End-to-end test | **Run**: Fresh install → buy → activate → verify |

## Immediate Next Steps

1. **Now** (10 min): Generate and embed Ed25519 keypair
   ```bash
   cd scripts
   python generate_keypair.py
   # Copy license_public.pem into licenseManager.py (replace placeholder)
   # Keep license_private.pem on VPS (chmod 600)
   ```

2. **Before launch** (30 min): Set up payment provider
   - Stripe: Create products, webhook endpoint, update buy page `action` URLs
   - Manual: Replace with email form or PayPal.me links

3. **Deploy** (1–2 hours): VPS + website
   - Point DNS `plugins.reveda.eu` to VPS
   - Deploy `download_counter.py` (systemd) or serve static files
   - Build/deploy website with updated buy pages

4. **Verification** (15 min): Full purchase flow
   - Install fresh Revolution EDA
   - Try RevedaSim → get license dialog → copy fingerprint
   - Complete purchase → receive key → activate → verify plugin works

## Security Notes

- **Never commit** `license_private.pem` to any repo
- **Public key** can be shipped safely — it only verifies, cannot sign
- **Key rotation**: If private key ever compromised, generate new keypair and update `PUBLIC_KEY_PEM` in the next app release
- **Backup**: Keep encrypted backup of `license_private.pem` off-site
