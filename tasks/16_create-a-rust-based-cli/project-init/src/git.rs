use anyhow::Result;
use git2::{Repository, Signature, Time, Oid};
use std::path::Path;
use crate::error::ProjectInitError;

pub fn initialize_git(project_path: &Path, project_name: &str) -> Result<()> {
    let repo = Repository::init(project_path)?;

    let mut index = repo.index()?;

    let path = project_path.to_path_buf();
    add_files_to_index(&mut index, &path)?;

    let tree_id = index.write_tree()?;
    let tree = repo.find_tree(tree_id)?;

    let sig = Signature::now("Project Init", "project-init@localhost")?;

    let head_commit = {
        let head_result = repo.head();
        match head_result {
            Ok(head) => Some(head.peel_to_commit()?),
            Err(_) => None,
        }
    };

    let parents = match head_commit {
        Some(ref commit) => vec![commit],
        None => vec![],
    };

    let message = format!("Initial commit: Initialize {} project", project_name);

    repo.commit(
        Some("HEAD"),
        &sig,
        &sig,
        &message,
        &tree,
        parents.as_slice(),
    )?;

    Ok(())
}

pub fn add_remote(repo_path: &Path, name: &str, url: &str) -> Result<()> {
    let repo = Repository::open(repo_path)?;

    repo.remote(name, url)?;

    println!("Added remote '{}' -> {}", name, url);

    Ok(())
}

pub fn create_initial_commit(repo_path: &Path, message: &str) -> Result<Oid> {
    let repo = Repository::open(repo_path)?;

    let mut index = repo.index()?;
    let tree_id = index.write_tree()?;
    let tree = repo.find_tree(tree_id)?;

    let sig = Signature::now("Project Init", "project-init@localhost")?;

    let commit_id = repo.commit(
        Some("HEAD"),
        &sig,
        &sig,
        message,
        &tree,
        &[],
    )?;

    Ok(commit_id)
}

fn add_files_to_index(index: &mut git2::Index, project_path: &Path) -> Result<()> {
    use walkdir::WalkDir;

    for entry in WalkDir::new(project_path)
        .min_depth(1)
        .into_iter()
        .filter_entry(|e| !is_git_entry(e))
    {
        let entry = entry?;
        let path = entry.path();

        if path.is_file() {
            let relative_path = path.strip_prefix(project_path)?;
            index.add_path(relative_path)?;
        }
    }

    Ok(())
}

fn is_git_entry(entry: &walkdir::DirEntry) -> bool {
    entry.file_name().to_string_lossy() == ".git"
}

pub fn check_git_installed() -> bool {
    std::path::Path::new("/usr/bin/git").exists() ||
    std::path::Path::new("/usr/local/bin/git").exists() ||
    which::which("git").is_ok()
}
