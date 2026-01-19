# RustVault Quick Start Guide

Get started with RustVault in 5 minutes!

## Installation

### Option 1: Build from Source
```bash
# Clone the repository
git clone https://github.com/example/rustvault.git
cd rustvault

# Build and install
cargo install --path .
```

### Option 2: Build Binary
```bash
cargo build --release
# Binary is at target/release/rustvault
```

## First-Time Setup

### 1. Initialize Your Vault
```bash
rustvault init
```

You'll be prompted to create a master password:
- **Minimum**: 8 characters
- **Recommended**: 4+ random words (e.g., `correct horse battery staple`)
- **⚠️ IMPORTANT**: Remember this password - there's no recovery!

### 2. Add Your First Password
```bash
rustvault entry add
```

Follow the prompts:
- **Title**: e.g., "GitHub"
- **Username**: e.g., "myuser@example.com"
- **Password**: type or paste (or generate one)

Or generate a secure password automatically:
```bash
rustvault entry add --title "GitHub" --username "myuser" --generate-password --password-length 24
```

### 3. Retrieve Your Password
```bash
# Show entry details
rustvault entry show "GitHub"

# Copy password to clipboard (auto-clears after 30s)
rustvault entry show "GitHub" --copy-password
```

## Common Tasks

### Generate a Strong Password
```bash
# 16-character password (default)
rustvault generate password

# 32-character password, no ambiguous characters
rustvault generate password --length 32 --exclude-ambiguous --copy

# 6-word passphrase
rustvault generate passphrase --words 6 --capitalize --include-number
```

### Organize with Folders
```bash
# Create folders
rustvault folder add "Personal"
rustvault folder add "Work"

# Add entry to folder
rustvault entry add --folder "Work" --title "Company VPN"
```

### Find Passwords Quickly
```bash
# Search by title, username, or tags
rustvault search "github"

# Show full details
rustvault search "work" --full
```

### Setup Two-Factor Authentication (TOTP)
```bash
# When adding an entry, provide the TOTP secret from your 2FA setup
# (Look for "manual setup" or "show secret" when enabling 2FA)
rustvault entry add --title "Google" --totp-secret "JBSWY3DPEHPK3PXP"

# Show TOTP code
rustvault totp "Google"
```

### Backup Your Vault
```bash
# Automatic backups are kept at ~/.config/rustvault/backups/
# Manual export (plaintext - use caution!)
rustvault export --plaintext ~/backup/vault-backup.json
```

## Daily Usage Workflow

### Typical Session
```bash
# 1. Unlock vault (first operation)
rustvault entry list

# 2. Get password for website
rustvault entry show "Reddit" --copy-password

# 3. Generate new password for account creation
rustvault generate password --length 20 --copy

# 4. Add new entry
rustvault entry add --title "NewSite" --username "me@example.com"

# 5. Vault auto-locks after 5 minutes
```

## Pro Tips

### 1. Use Passphrases for Master Password
```
Good: "correct horse battery staple" (~50 bits of entropy)
Better: "correct-horse-battery-staple-42" (~70 bits)
Best: 4-7 random words from a diceware list
```

### 2. Enable Clipboard Auto-Clear
```bash
# Passwords auto-clear from clipboard after 30 seconds
rustvault entry show "GitHub" --copy-password
# → Clipboard cleared automatically
```

### 3. Use Tags for Organization
```bash
rustvault entry add --title "Work Email" --tags "work,important,email"
rustvault entry add --title "Personal Email" --tags "personal,email"

rustvault search "email"
```

### 4. Generate Strong Passwords
```bash
# High-security accounts (banking, etc.)
rustvault generate password --length 32 --exclude-ambiguous

# Everything else
rustvault generate passphrase --words 5 --include-number
```

### 5. Regular Backups
```bash
# Check backup location
ls ~/.config/rustvault/backups/

# Export encrypted backup periodically
rustvault export --plaintext ~/encrypted-backups/vault-$(date +%Y%m%d).json
```

## Troubleshooting

### "Vault not found"
```bash
# Initialize vault first
rustvault init
```

### "Incorrect master password"
- Check caps lock
- Try variations you might have used
- ⚠️ No recovery option - this is by design!

### "Vault is locked by another process"
```bash
# Wait a few seconds, or kill the locking process
# On Linux/Mac:
lsof ~/.config/rustvault/vault.rustvault
```

### Clipboard not working
```bash
# Install clipboard dependencies:
# Linux: sudo apt install xclip
# macOS: included
# Windows: included
```

## Security Checklist

- ✅ Use a **strong, unique master password**
- ✅ Keep **offline backups** of your vault
- ✅ Enable **2FA** where available
- ✅ Use **different passwords** for each account
- ✅ Generate **strong random passwords**
- ✅ **Don't forget** your master password!
- ✅ Keep **RustVault updated**
- ✅ Be careful with **plaintext exports**

## Next Steps

- Read the full [README.md](README.md) for all features
- Check [examples/basic_usage.sh](examples/basic_usage.sh) for more examples
- Review [CONTRIBUTING.md](CONTRIBUTING.md) if you want to contribute
- Audit the code for security (it's open source!)

## Need Help?

- Open an issue on GitHub
- Check existing documentation
- Read the code comments

---

**🔐 Happy password managing!**

Remember: Your master password is the key to your entire digital life. Keep it safe and memorable!
