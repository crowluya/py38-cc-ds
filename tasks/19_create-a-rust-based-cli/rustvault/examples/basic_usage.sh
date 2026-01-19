#!/bin/bash
# RustVault Basic Usage Examples
# This script demonstrates common RustVault operations

set -e

echo "🔐 RustVault Basic Usage Examples"
echo "=================================="
echo ""

# Note: These are example commands. In production, you would run these interactively.

# Example 1: Initialize a new vault
echo "1. Initialize a new vault:"
echo "   $ rustvault init"
echo ""

# Example 2: Add a password entry
echo "2. Add a password entry:"
echo "   $ rustvault entry add --title 'GitHub' --username 'myuser@example.com'"
echo ""

# Example 3: Add an entry with generated password
echo "3. Add an entry with auto-generated password:"
echo "   $ rustvault entry add --title 'AWS' --username 'admin@example.com' --generate-password --password-length 24"
echo ""

# Example 4: List all entries
echo "4. List all entries:"
echo "   $ rustvault entry list"
echo ""

# Example 5: Show entry details
echo "5. Show entry details:"
echo "   $ rustvault entry show 'GitHub'"
echo ""

# Example 6: Copy password to clipboard
echo "6. Copy password to clipboard:"
echo "   $ rustvault entry show 'GitHub' --copy-password"
echo ""

# Example 7: Generate a secure password
echo "7. Generate a secure password:"
echo "   $ rustvault generate password --length 24 --exclude-ambiguous --show-strength"
echo ""

# Example 8: Generate a passphrase
echo "8. Generate a passphrase:"
echo "   $ rustvault generate passphrase --words 6 --capitalize --include-number"
echo ""

# Example 9: Create folders
echo "9. Create folders for organization:"
echo "   $ rustvault folder add 'Personal'"
echo "   $ rustvault folder add 'Work' --parent ''"
echo "   $ rustvault folder add 'Projects' --parent 'Work'"
echo ""

# Example 10: Add entry to specific folder
echo "10. Add entry to specific folder:"
echo "    $ rustvault entry add --title 'Company VPN' --folder 'Work' --username 'user@company.com'"
echo ""

# Example 11: Search entries
echo "11. Search for entries:"
echo "    $ rustvault search 'github'"
echo "    $ rustvault search 'work' --full"
echo ""

# Example 12: Show TOTP code
echo "12. Show TOTP code (if configured):"
echo "    $ rustvault totp 'GitHub'"
echo ""

# Example 13: Export vault (WARNING: plaintext!)
echo "13. Export vault (use with caution!):"
echo "    $ rustvault export --plaintext ~/backup/vault.json"
echo ""

# Example 14: Check vault status
echo "14. Check vault status:"
echo "    $ rustvault status"
echo ""

echo "=================================="
echo "For more information, run: rustvault --help"
echo "Or read the documentation at: https://github.com/example/rustvault"
