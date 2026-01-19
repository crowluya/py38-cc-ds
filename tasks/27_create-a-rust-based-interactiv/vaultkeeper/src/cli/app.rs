use crate::clipboard::ClipboardManager;
use crate::config::Config;
use crate::vault::{Vault, VaultEntry};
use crate::validation::{analyze_password, PasswordStrength};
use crossterm::event::KeyCode;
use std::sync::Arc;

/// Application state
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AppState {
    Browsing,
    ViewingEntry,
    AddingEntry,
    EditingEntry,
    ConfirmingDelete,
}

/// Input mode
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InputMode {
    Normal,
    Search,
    Form,
}

/// Main application state holder
pub struct App {
    vault: Option<Vault>,
    state: AppState,
    input_mode: InputMode,
    selected_index: usize,
    search_query: String,
    filtered_entries: Vec<usize>,
    config: Config,
    clipboard_manager: Option<ClipboardManager>,

    // Form fields
    form_field: usize,
    form_title: String,
    form_username: String,
    form_password: String,
    form_url: String,
    form_notes: String,
}

impl App {
    pub fn new(config: Config) -> Self {
        Self {
            vault: None,
            state: AppState::Browsing,
            input_mode: InputMode::Normal,
            selected_index: 0,
            search_query: String::new(),
            filtered_entries: Vec::new(),
            config,
            clipboard_manager: ClipboardManager::new().ok(),
            form_field: 0,
            form_title: String::new(),
            form_username: String::new(),
            form_password: String::new(),
            form_url: String::new(),
            form_notes: String::new(),
        }
    }

    pub fn set_vault(&mut self, vault: Vault) {
        self.vault = Some(vault);
        self.update_filtered_entries();
    }

    pub fn get_vault(&self) -> &Vault {
        self.vault.as_ref().unwrap()
    }

    pub fn get_vault_mut(&mut self) -> &mut Vault {
        self.vault.as_mut().unwrap()
    }

    pub fn update_filtered_entries(&mut self) {
        let vault = self.get_vault();
        self.filtered_entries = if self.search_query.is_empty() {
            (0..vault.entries.len()).collect()
        } else {
            vault
                .search_entries(&self.search_query)
                .iter()
                .map(|entry| {
                    vault
                        .entries
                        .iter()
                        .position(|e| e.id == entry.id)
                        .unwrap()
                })
                .collect()
        };
        self.selected_index = 0;
    }

    pub fn filtered_entries(&self) -> Vec<&VaultEntry> {
        let vault = self.get_vault();
        self.filtered_entries
            .iter()
            .map(|&i| &vault.entries[i])
            .collect()
    }

    pub fn selected_entry(&self) -> Option<&VaultEntry> {
        let vault = self.get_vault();
        self.filtered_entries
            .get(self.selected_index)
            .map(|&i| &vault.entries[i])
    }

    pub fn handle_key_event(&mut self, key: crossterm::event::KeyEvent) -> bool {
        // Should quit?
        if key.code == KeyCode::Char('q') && self.state == AppState::Browsing {
            return true;
        }

        match self.state {
            AppState::Browsing => self.handle_browsing(key),
            AppState::ViewingEntry => self.handle_viewing_entry(key),
            AppState::AddingEntry => self.handle_form_input(key, true),
            AppState::EditingEntry => self.handle_form_input(key, false),
            AppState::ConfirmingDelete => self.handle_confirm_delete(key),
        }

        false
    }

    fn handle_browsing(&mut self, key: crossterm::event::KeyEvent) {
        match key.code {
            KeyCode::Char('/') | KeyCode::Char('s') => {
                self.input_mode = InputMode::Search;
                self.search_query.clear();
            }
            KeyCode::Char('a') => {
                self.state = AppState::AddingEntry;
                self.input_mode = InputMode::Form;
                self.clear_form();
            }
            KeyCode::Enter => {
                if self.selected_entry().is_some() {
                    self.state = AppState::ViewingEntry;
                }
            }
            KeyCode::Char('d') => {
                if self.selected_entry().is_some() {
                    self.state = AppState::ConfirmingDelete;
                }
            }
            KeyCode::Up => {
                if self.selected_index > 0 {
                    self.selected_index -= 1;
                }
            }
            KeyCode::Down => {
                if self.selected_index < self.filtered_entries.len().saturating_sub(1) {
                    self.selected_index += 1;
                }
            }
            KeyCode::Esc => {
                self.input_mode = InputMode::Normal;
                self.search_query.clear();
                self.update_filtered_entries();
            }
            KeyCode::Char(c) if self.input_mode == InputMode::Search => {
                self.search_query.push(c);
                self.update_filtered_entries();
            }
            KeyCode::Backspace if self.input_mode == InputMode::Search => {
                self.search_query.pop();
                self.update_filtered_entries();
            }
            _ => {}
        }
    }

    fn handle_viewing_entry(&mut self, key: crossterm::event::KeyEvent) {
        match key.code {
            KeyCode::Esc => {
                self.state = AppState::Browsing;
            }
            KeyCode::Char('c') => {
                if let Some(entry) = self.selected_entry() {
                    if let Some(clipboard) = &self.clipboard_manager {
                        let _ = clipboard.copy(entry.password.as_str());
                    }
                }
            }
            KeyCode::Char('e') => {
                if let Some(entry) = self.selected_entry() {
                    self.populate_form_from_entry(entry);
                    self.state = AppState::EditingEntry;
                }
            }
            _ => {}
        }
    }

    fn handle_form_input(&mut self, key: crossterm::event::KeyEvent, is_new: bool) {
        match key.code {
            KeyCode::Esc => {
                if is_new {
                    self.state = AppState::Browsing;
                } else {
                    // Cancel editing, go back to viewing
                    self.state = AppState::ViewingEntry;
                }
                self.input_mode = InputMode::Normal;
            }
            KeyCode::Enter => {
                if self.validate_and_save_entry(is_new) {
                    self.state = AppState::Browsing;
                    self.input_mode = InputMode::Normal;
                    self.update_filtered_entries();
                }
            }
            KeyCode::Tab => {
                self.form_field = (self.form_field + 1) % 5;
            }
            KeyCode::BackTab => {
                self.form_field = if self.form_field == 0 {
                    4
                } else {
                    self.form_field - 1
                };
            }
            KeyCode::Char(c) => {
                self.update_form_field(c);
            }
            KeyCode::Backspace => {
                self.remove_from_form_field();
            }
            _ => {}
        }
    }

    fn handle_confirm_delete(&mut self, key: crossterm::event::KeyEvent) {
        match key.code {
            KeyCode::Char('y') | KeyCode::Char('Y') => {
                if let Some(entry) = self.selected_entry() {
                    self.get_vault_mut().remove_entry(&entry.id);
                    self.update_filtered_entries();
                }
                self.state = AppState::Browsing;
            }
            KeyCode::Char('n') | KeyCode::Esc => {
                self.state = AppState::Browsing;
            }
            _ => {}
        }
    }

    fn clear_form(&mut self) {
        self.form_field = 0;
        self.form_title.clear();
        self.form_username.clear();
        self.form_password.clear();
        self.form_url.clear();
        self.form_notes.clear();
    }

    fn populate_form_from_entry(&mut self, entry: &VaultEntry) {
        self.form_title = entry.title.clone();
        self.form_username = entry.username.clone();
        self.form_password = entry.password.as_str().to_string();
        self.form_url = entry.url.clone().unwrap_or_default();
        self.form_notes = entry.notes.clone().unwrap_or_default();
        self.form_field = 0;
    }

    fn update_form_field(&mut self, c: char) {
        match self.form_field {
            0 => self.form_title.push(c),
            1 => self.form_username.push(c),
            2 => self.form_password.push(c),
            3 => self.form_url.push(c),
            4 => self.form_notes.push(c),
            _ => {}
        }
    }

    fn remove_from_form_field(&mut self) {
        match self.form_field {
            0 => self.form_title.pop(),
            1 => self.form_username.pop(),
            2 => self.form_password.pop(),
            3 => self.form_url.pop(),
            4 => self.form_notes.pop(),
            _ => None,
        };
    }

    fn validate_and_save_entry(&mut self, is_new: bool) -> bool {
        // Validate required fields
        if self.form_title.is_empty() || self.form_username.is_empty() || self.form_password.is_empty() {
            return false;
        }

        // Check password strength
        let analysis = analyze_password(&self.form_password, &[]);
        if analysis.strength == PasswordStrength::Weak {
            // Could show warning here
        }

        let vault = self.get_vault_mut();

        if is_new {
            let entry = VaultEntry::new(
                self.form_title.clone(),
                self.form_username.clone(),
                self.form_password.clone(),
            )
            .with_url(self.form_url.clone())
            .with_notes(self.form_notes.clone());

            vault.add_entry(entry);
        } else if let Some(entry) = self.selected_entry() {
            let id = entry.id.clone();
            vault.update_entry(&id, |e| {
                e.title = self.form_title.clone();
                e.username = self.form_username.clone();
                e.update_password(self.form_password.clone());
                e.url = if self.form_url.is_empty() {
                    None
                } else {
                    Some(self.form_url.clone())
                };
                e.notes = if self.form_notes.is_empty() {
                    None
                } else {
                    Some(self.form_notes.clone())
                };
            });
        }

        true
    }
}
