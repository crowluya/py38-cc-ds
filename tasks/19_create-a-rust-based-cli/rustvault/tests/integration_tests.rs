//! Integration tests for RustVault
//!
//! These tests verify end-to-end functionality of the password manager.

use rustvault::{
    generate_password, generate_passphrase, PasswordPolicy, PassphrasePolicy, Vault, VaultEntry,
    VaultStorage,
};
use tempfile::TempDir;

#[test]
fn test_vault_workflow() {
    let temp_dir = TempDir::new().unwrap();
    let vault_path = temp_dir.path().join("test_vault");
    let storage = VaultStorage::new(vault_path);

    // Test vault creation
    let master_password = "test_master_password_123";
    storage.create_vault(master_password).unwrap();
    assert!(storage.vault_exists());

    // Test vault loading
    let loaded_vault = storage.load_vault(master_password).unwrap();
    assert_eq!(loaded_vault.version, 1);
    assert_eq!(loaded_vault.metadata.entry_count, 0);

    // Test adding entry
    let mut vault = loaded_vault;
    let entry = VaultEntry::new(
        "Test Entry".to_string(),
        "testuser".to_string(),
        "testpass".to_string(),
    );
    vault.add_entry("", entry).unwrap();
    assert_eq!(vault.metadata.entry_count, 1);

    // Test saving
    storage.save_vault(&vault, master_password).unwrap();

    // Test reloading
    let reloaded_vault = storage.load_vault(master_password).unwrap();
    assert_eq!(reloaded_vault.metadata.entry_count, 1);

    let entries = reloaded_vault.list_entries("");
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].title, "Test Entry");
}

#[test]
fn test_folder_workflow() {
    let mut vault = Vault::new();

    // Create folders
    vault.create_folder("personal", "Personal").unwrap();
    vault.create_folder("work", "Work").unwrap();
    vault.create_folder("work/projects", "Projects").unwrap();

    // Verify folders exist
    assert!(vault.get_folder("personal").is_some());
    assert!(vault.get_folder("work").is_some());
    assert!(vault.get_folder("work/projects").is_some());

    // Add entries to different folders
    let entry1 = VaultEntry::new(
        "Personal Site".to_string(),
        "user1".to_string(),
        "pass1".to_string(),
    );
    let entry2 =
        VaultEntry::new("Work App".to_string(), "user2".to_string(), "pass2".to_string());

    vault.add_entry("personal", entry1).unwrap();
    vault.add_entry("work", entry2).unwrap();

    // Verify entries in correct folders
    let personal_entries = vault.list_entries("personal");
    let work_entries = vault.list_entries("work");

    assert_eq!(personal_entries.len(), 1);
    assert_eq!(work_entries.len(), 1);
    assert_eq!(personal_entries[0].title, "Personal Site");
    assert_eq!(work_entries[0].title, "Work App");
}

#[test]
fn test_password_generation() {
    // Test default policy
    let policy = PasswordPolicy::default();
    let password = generate_password(&policy).unwrap();
    assert_eq!(password.len(), 16);

    // Test custom length
    let policy = PasswordPolicy::new(32);
    let password = generate_password(&policy).unwrap();
    assert_eq!(password.len(), 32);

    // Test no symbols
    let mut policy = PasswordPolicy::new(20);
    policy.symbols = false;
    let password = generate_password(&policy).unwrap();
    assert!(password.chars().all(|c| c.is_alphanumeric()));
    assert_eq!(password.len(), 20);
}

#[test]
fn test_passphrase_generation() {
    // Test default policy
    let policy = PassphrasePolicy::default();
    let passphrase = generate_passphrase(&policy).unwrap();
    let word_count = passphrase.split('-').count();
    assert_eq!(word_count, 5);

    // Test custom word count
    let policy = PassphrasePolicy {
        word_count: 8,
        ..Default::default()
    };
    let passphrase = generate_passphrase(&policy).unwrap();
    let word_count = passphrase.split('-').count();
    assert_eq!(word_count, 8);

    // Test with number
    let policy = PassphrasePolicy {
        include_number: true,
        ..Default::default()
    };
    let passphrase = generate_passphrase(&policy).unwrap();
    assert!(passphrase.chars().any(|c| c.is_ascii_digit()));
}

#[test]
fn test_search_functionality() {
    let mut vault = Vault::new();

    // Add multiple entries
    let entry1 = VaultEntry::new(
        "GitHub Account".to_string(),
        "githubuser".to_string(),
        "pass1".to_string(),
    );
    let entry2 = VaultEntry::new(
        "GitLab Repository".to_string(),
        "gitlabuser".to_string(),
        "pass2".to_string(),
    );
    let entry3 = VaultEntry::new(
        "AWS Console".to_string(),
        "awsuser".to_string(),
        "pass3".to_string(),
    );

    vault.add_entry("", entry1).unwrap();
    vault.add_entry("", entry2).unwrap();
    vault.add_entry("", entry3).unwrap();

    // Test search
    let results = vault.search("git");
    assert_eq!(results.len(), 2);

    let results = vault.search("github");
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].entry.title, "GitHub Account");
}

#[test]
fn test_entry_deletion() {
    let mut vault = Vault::new();

    let entry = VaultEntry::new("Test".to_string(), "user".to_string(), "pass".to_string());
    vault.add_entry("", entry.clone()).unwrap();
    assert_eq!(vault.metadata.entry_count, 1);

    vault.delete_entry("", &entry.id).unwrap();
    assert_eq!(vault.metadata.entry_count, 0);

    let entries = vault.list_entries("");
    assert_eq!(entries.len(), 0);
}

#[test]
fn test_export_import_roundtrip() {
    let temp_dir = TempDir::new().unwrap();
    let vault_path = temp_dir.path().join("test_vault");
    let export_path = temp_dir.path().join("export.json");
    let import_path = temp_dir.path().join("import_vault");
    let storage = VaultStorage::new(vault_path);

    let master_password = "test_password_123";

    // Create and populate vault
    storage.create_vault(master_password).unwrap();
    let mut vault = storage.load_vault(master_password).unwrap();

    let entry = VaultEntry::new(
        "Test Entry".to_string(),
        "testuser".to_string(),
        "testpass".to_string(),
    );
    vault.add_entry("", entry).unwrap();
    storage.save_vault(&vault, master_password).unwrap();

    // Export
    storage.export_decrypted(master_password, &export_path).unwrap();
    assert!(export_path.exists());

    // Import to new vault
    let import_storage = VaultStorage::new(import_path);
    import_storage
        .import_decrypted(&export_path, master_password)
        .unwrap();

    // Verify imported vault
    let imported_vault = import_storage.load_vault(master_password).unwrap();
    assert_eq!(imported_vault.metadata.entry_count, 1);
}

#[test]
fn test_totp_generation() {
    use rustvault::{generate_totp_default, generate_secret};

    // Test secret generation
    let secret = generate_secret();
    assert!(!secret.is_empty());

    // Test TOTP generation
    let totp = generate_totp_default(&secret).unwrap();
    assert_eq!(totp.code.len(), 6);
    assert!(totp.remaining_seconds > 0);
    assert!(totp.remaining_seconds <= 30);
}

#[test]
fn test_invalid_password() {
    let temp_dir = TempDir::new().unwrap();
    let vault_path = temp_dir.path().join("test_vault");
    let storage = VaultStorage::new(vault_path);

    let correct_password = "correct_password_123";
    storage.create_vault(correct_password).unwrap();

    // Try to load with wrong password
    let result = storage.load_vault("wrong_password");
    assert!(result.is_err());
}

#[test]
fn test_password_strength() {
    use rustvault::{estimate_strength, PasswordStrength};

    let weak = "password";
    let fair = "Password1";
    let good = "Password123!";
    let strong = "MyStr0ng!P@ssw0rd#2024$";

    assert_eq!(estimate_strength(weak), PasswordStrength::Weak);
    assert_eq!(estimate_strength(fair), PasswordStrength::Fair);
    assert!(estimate_strength(good) >= PasswordStrength::Good);
    assert!(estimate_strength(strong) >= PasswordStrength::Strong);
}
