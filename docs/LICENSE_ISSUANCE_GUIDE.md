# How to Issue Revolution EDA Licenses

This guide explains how to generate and issue Ed25519 license keys for Revolution EDA plugins.

## Overview

Revolution EDA uses **Ed25519 cryptographic signatures** for license keys:
- **Offline validation** - No internet required after activation
- **Node-locked** - Tied to customer's machine fingerprint
- **Secure** - Cryptographically signed, tamper-proof
- **Simple** - Just email the key to the customer

## One-Time Setup (First Time Only)

### Step 1: Generate Your Keypair

Run this command **once** to create your signing keys:

```bash
cd /path/to/revolution-eda
python scripts/generate_license.py --generate-keypair
```

This creates two files:
- `license_private_key.pem` - **KEEP SECRET!** Never share this.
- `license_public_key.pem` - Public key (already embedded in the app)

**Security:**
- Store `license_private_key.pem` on a secure server
- Back it up in a safe location
- Never commit it to git
- Never send it to anyone

### Step 2: Verify Public Key

The public key should already be in `revedaLicense/licenseManager.py`:

```python
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAYSnG7/SFnxzvnRW+/EOapUjGrR0cxP9BpvcV7834zh0=
-----END PUBLIC KEY-----"""
```

If you generated a new keypair, replace this with your new public key.

## Issuing Licenses (For Each Customer)

### Step 1: Get Customer's Machine Fingerprint

The customer runs Revolution EDA and clicks on a paid plugin. The license dialog shows their **machine fingerprint** (16-character hex string like `a3f7b2d9e8c14f56`).

They should copy and send this to you via email.

**Alternative:** They can run this command:
```bash
python test_license.py
```

### Step 2: Generate License Key

#### For a Subscription License (expires after X days):

```bash
python scripts/generate_license.py \
    --plugin revedasim \
    --machine-hash a3f7b2d9e8c14f56 \
    --type subscription \
    --days 365
```

#### For a Perpetual License (never expires):

```bash
python scripts/generate_license.py \
    --plugin revedasim \
    --machine-hash a3f7b2d9e8c14f56 \
    --type perpetual
```

#### For a Specific Expiry Date:

```bash
python scripts/generate_license.py \
    --plugin revedasim \
    --machine-hash a3f7b2d9e8c14f56 \
    --type subscription \
    --expiry 2025-12-31
```

### Step 3: Send Key to Customer

The script outputs a license key like:

```
eyJlIjoiMjAyNS0xMi0zMSIsIm0iOiJhM2Y3YjJkOWU4YzE0ZjU2IiwicCI6InJldmVkYXNpbSIsInQiOiJzdWJzY3JpcHRpb24ifQ.xK8vN2mP9qR5tL3wY7zB4cD6eF1gH8iJ0kM2nO4pQ6rS8tU9vW1xY3zA5bC7dE9fG1hI3jK5lM7nO9pQ2rS4tU
```

**Email this key to the customer** with instructions:

```
Subject: Your Revolution EDA License Key

Hi [Customer Name],

Thank you for purchasing [Plugin Name]!

Your license key is:

[PASTE KEY HERE]

To activate:
1. Open Revolution EDA
2. Click on the [Plugin Name] menu item
3. Paste the license key into the dialog
4. Click "Activate"

The license is tied to your machine and will work offline.

Plugin: [Plugin Name]
Type: [Subscription/Perpetual]
Expiry: [Date or "Never"]

If you need to transfer the license to a new machine, please contact us.

Best regards,
Revolution Semiconductor
```

## Plugin Names

Use these exact plugin names when generating keys:

- `revedasim` - Simulation plugin
- `revedaPlot` - Plotting plugin  
- `aiTerminal` - AI Terminal plugin

## Testing a License Key

Before sending to customer, test the key:

```bash
python test_license.py \
    --validate \
    --plugin revedasim \
    --key "eyJlIjoiMjAyNS0xMi0zMSIsIm0iOiJhM2Y3YjJkOWU4YzE0ZjU2IiwicCI6InJldmVkYXNpbSIsInQiOiJzdWJzY3JpcHRpb24ifQ.xK8vN2mP9qR5tL3wY7zB4cD6eF1gH8iJ0kM2nO4pQ6rS8tU9vW1xY3zA5bC7dE9fG1hI3jK5lM7nO9pQ2rS4tU"
```

**Note:** This will only work if you run it on the customer's machine (or have their exact machine fingerprint).

## Customer Activation Process

1. Customer opens Revolution EDA
2. Clicks on a paid plugin menu item
3. License dialog appears showing:
   - Plugin name
   - Machine fingerprint (they send this to you)
   - "Buy License" button (optional, if payment_url configured)
   - License key input field
4. Customer pastes the key you sent
5. Clicks "Activate"
6. Key is validated and stored in `~/.reveda/licenses/{plugin}.lic`
7. Plugin is now unlocked

## Troubleshooting

### "Invalid license key" error

Possible causes:
- Wrong machine fingerprint (key is for different machine)
- Wrong plugin name
- Expired subscription
- Typo in the key (missing characters)

### Customer changed machines

Generate a new key with their new machine fingerprint. The old key won't work on the new machine (node-locked).

### License expired

Generate a new key with a new expiry date.

## Advanced Options

### Custom Private Key Location

```bash
python scripts/generate_license.py \
    --private-key /secure/path/to/private_key.pem \
    --plugin revedasim \
    --machine-hash a3f7b2d9e8c14f56 \
    --type subscription \
    --days 365
```

### Batch License Generation

Create a script to generate multiple licenses:

```bash
#!/bin/bash
# generate_batch_licenses.sh

CUSTOMERS=(
    "customer1@example.com:a3f7b2d9e8c14f56:revedasim"
    "customer2@example.com:b4e8c3f0a9d25e67:revedaPlot"
)

for entry in "${CUSTOMERS[@]}"; do
    IFS=':' read -r email fingerprint plugin <<< "$entry"
    echo "Generating license for $email ($plugin)..."
    
    python scripts/generate_license.py \
        --plugin "$plugin" \
        --machine-hash "$fingerprint" \
        --type subscription \
        --days 365 > "license_${email}_${plugin}.txt"
    
    echo "Saved to license_${email}_${plugin}.txt"
done
```

## Security Best Practices

1. **Never share the private key** - It can generate unlimited valid licenses
2. **Store private key securely** - Use encrypted storage, access controls
3. **Back up the private key** - If lost, you can't generate new licenses
4. **Rotate keys periodically** - Generate new keypair every 1-2 years
5. **Log license generation** - Keep records of who got what license
6. **Validate customer identity** - Before sending machine fingerprint

## Payment Integration

Since Polar.sh was removed, you need to handle payments yourself:

### Option 1: Manual Process
1. Customer pays via PayPal/Stripe/bank transfer
2. You receive payment notification
3. Customer emails you their machine fingerprint
4. You generate and email the license key

### Option 2: Automated (requires development)
1. Set up payment processor (Stripe, Paddle, etc.)
2. Create webhook to receive payment notifications
3. Automatically generate license key
4. Email key to customer

### Option 3: Use a Different MOR
- Gumroad
- Paddle
- FastSpring
- Lemon Squeezy

Configure `payment_url` in plugin `config.json` to point to your checkout page.

## Files Reference

- `scripts/generate_license.py` - License key generator (server-side)
- `test_license.py` - License key validator (testing)
- `revedaLicense/licenseManager.py` - License validation (client-side)
- `license_private_key.pem` - Your private signing key (KEEP SECRET)
- `license_public_key.pem` - Public verification key (in app)

## Quick Reference

```bash
# Generate keypair (once)
python scripts/generate_license.py --generate-keypair

# Generate 1-year subscription
python scripts/generate_license.py --plugin revedasim --machine-hash HASH --type subscription --days 365

# Generate perpetual license
python scripts/generate_license.py --plugin revedasim --machine-hash HASH --type perpetual

# Test a license key
python test_license.py --validate --plugin revedasim --key "KEY"

# Get machine fingerprint
python test_license.py
```

---

**Need Help?**
- Check `docs/POLAR_REMOVAL_SUMMARY.md` for what changed
- Review `revedaLicense/licenseManager.py` for validation logic
- Contact Revolution Semiconductor support
