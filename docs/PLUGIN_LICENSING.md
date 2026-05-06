# Plugin Licensing System

This document describes the node-locked subscription and perpetual license system for commercial Revolution EDA plugins.

## Overview

Paid plugins (`revedasim`, `revedaPlot`, `aiTerminal`) require a valid license key to activate. The system is:

- **Node-locked** — each key is tied to a single machine fingerprint
- **Cryptographically signed** — HMAC-SHA256 prevents tampering
- **Offline-validated** — no network calls needed after activation
- **Subscription or perpetual** — monthly (€5) or one-time (€50) options

## Architecture

```
┌─────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  User Machine   │────▶│ LicenseManager.py   │────▶│ ~/.reveda/       │
│  (Revolution    │     │ (validate, store,   │     │ licenses/        │
│   EDA app)      │◄────│  prompt dialog)     │◄────│ {plugin}.lic     │
└─────────────────┘     └─────────────────────┘     └──────────────────┘
          │
          │ opens browser
          ▼
┌─────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  reveda.eu      │────▶│ Payment Provider    │────▶│ generate_license │
│  (buy page)     │     │ (Stripe, PayPal…)   │     │ .py (server-side)│
└─────────────────┘     └─────────────────────┘     └──────────────────┘
                                                              │
                                                              ▼
                                                       ┌──────────────┐
                                                       │ Email key to │
                                                       │ customer     │
                                                       └──────────────┘
```

## Files

### Client-side (in `revolution-eda/`)

| File | Role |
|------|------|
| `revedaEditor/backend/licenseManager.py` | Key validation, machine fingerprint, Qt dialog, local storage |
| `revedaEditor/backend/pluginsLoader.py` | Wraps plugin callbacks and view entry points with license gate |
| `scripts/generate_license.py` | Standalone server-side key generator |

### Web (in `reveda_website/`)

| File | Role |
|------|------|
| `src/pages/buy/revedasim.astro` | Checkout page for RevedaSim |
| `src/pages/buy/revedaPlot.astro` | Checkout page for RevedaPlot |
| `src/pages/buy/aiterminal.astro` | Checkout page for AI Terminal |
| `src/pages/plugins.astro` | Listing with "Buy License" CTA buttons |

## How It Works

### 1. First-time use

When the user clicks a licensed plugin menu item or opens a licensed view type:

1. `pluginsLoader._wrap_callback_with_license()` intercepts the call
2. `licenseManager.check_and_prompt_license()` checks `~/.reveda/licenses/{plugin}.lic`
3. If missing or invalid, a `LicenseDialog` is shown with:
   - **Buy License** button → opens `payment_url` in browser (reveda.eu/buy/…)
   - **Activate** button → prompts for license key paste

### 2. Purchasing a license

1. User visits `https://reveda.eu/buy/revedasim` or `/buy/revedaPlot`
2. Fills email + **Machine Fingerprint** (shown in the license dialog)
3. Selects **Monthly Subscription** (€5) or **Perpetual** (€50)
4. Completes payment via third-party provider
5. Server runs `generate_license.py` with the machine hash
6. Signed key is emailed to the user

### 3. Activating

1. User copies key from email into the dialog
2. `licenseManager.validate_license_key()` verifies:
   - HMAC signature matches shared secret
   - Plugin name matches
   - Machine fingerprint matches current computer
   - Expiry date is in the future (subscriptions only)
3. On success, key is saved to `~/.reveda/licenses/{plugin}.lic`
4. Plugin runs normally on every future launch

## License Key Format

```
base64(payload_json).truncated_hmac_signature
```

Payload (sorted keys, no whitespace):
```json
{"e":"2026-06-04","m":"a3f7b2d9e8c1...","p":"revedasim","t":"subscription"}
```

- `p` — plugin name
- `m` — machine fingerprint (SHA-256 of MAC + hostname, first 16 hex chars)
- `e` — expiry ISO date (empty for perpetual)
- `t` — `subscription` or `onetime`

## Server-Side Key Generation

```bash
python scripts/generate_license.py \
  --plugin revedasim \
  --machine-hash a3f7b2d9e8c1... \
  --type subscription \
  --days 30
```

Output:
```
Plugin:      revedasim
Machine:     a3f7b2d9e8c1...
Type:        subscription
Expiry:      2026-06-04
License Key: eyJlIjoiMjAyNi0wNi0wNCIsIm0iOiJhM2Y3YjJkOWU4YzEiLCJwIjoicmV2ZWRhc2ltIiwidCI6InN1YnNjcmlwdGlvbiJ9.7a8f3b2c1d0e9f4a
```

Email this key to the customer.

## Integration Points

### Plugin config (`config.json`)

A plugin is treated as licensed if its `config.json` contains:

```json
{
  "license": "Commercial",
  "payment_url": "https://reveda.eu/buy/revedasim"
}
```

Any of `"Commercial"`, `"Proprietary"`, or `"Paid"` (or `license_required: true`) triggers the gate.

### Registry (`plugins.json`)

The plugin registry also carries the payment URL so the registry window can display pricing links:

```json
{
  "name": "revedasim",
  "license": "Proprietary",
  "payment_url": "https://reveda.eu/buy/revedasim"
}
```

## Security Notes

- `LICENSE_SECRET` in both `licenseManager.py` and `generate_license.py` **must be changed** to a cryptographically random string before shipping. Treat it as a server secret — never commit the real value to a public repo.
- The key is tied to `uuid.getnode()` + `platform.node()`. Replacing a network card or changing the hostname invalidates the license. This is intentional for node-locking.
- Keys are stored as plain text in `~/.reveda/licenses/`, but tampering is detected because the HMAC will fail.

## Next Steps to Production

1. **Set the shared secret**
   ```bash
   # Generate a strong secret
   openssl rand -hex 32
   # Paste it into both files, replacing CHANGE_ME_BEFORE_SHIPPING
   ```
   - `revedaEditor/backend/licenseManager.py`
   - `scripts/generate_license.py`

2. **Choose and integrate a payment provider**
   - **Stripe**: create Checkout sessions that redirect back to a success page. On `checkout.session.completed` webhook, extract `machine_fingerprint` from metadata, run `generate_license.py`, and email the key.
   - **PayPal**: similar flow using PayPal Buttons + webhook listener.
   - **Simplest fallback**: keep the `submit-form.com` form, manually collect responses, and run the generator script by hand.

3. **Update the form action URLs**
   In `reveda_website/src/pages/buy/revedasim.astro` and `revedaPlot.astro`, replace:
   ```
   action="https://submit-form.com/your-payment-form-endpoint"
   ```
   with your real Stripe Checkout URL or form handler.

4. **Build and deploy the website**
   ```bash
   cd reveda_website
   npm run build
   # Deploy dist/ to your hosting (Netlify, Vercel, or your server)
   ```

5. **Test end-to-end**
   - Install a fresh copy of Revolution EDA (no `~/.reveda/licenses/`)
   - Click Simulation → verify the license dialog appears
   - Copy machine fingerprint from the dialog
   - Run `generate_license.py` with that fingerprint
   - Paste the generated key → verify activation succeeds
   - Restart the app → verify plugin works without re-prompting
   - Move the key to another machine → verify it fails validation

6. **Automate license delivery (optional)**
   A minimal serverless webhook handler (e.g., Netlify Function or Vercel API route):
   ```python
   # pseudo-code for Stripe webhook
   def handle_checkout_completed(event):
       machine_fp = event.metadata['machine_fingerprint']
       plugin = event.metadata['plugin']
       lic_type = event.metadata['license_type']
       days = 30 if lic_type == 'subscription' else 0
       key = generate_license_key(plugin, machine_fp, ..., lic_type)
       send_email(event.customer_email, subject='Your Revolution EDA License Key', body=key)
   ```

7. **Update plugin docs**
   Mention the licensing requirement on the website plugin pages (`revedaplot.md`, `spice-simulation.md`) and in the Revolution EDA README.
