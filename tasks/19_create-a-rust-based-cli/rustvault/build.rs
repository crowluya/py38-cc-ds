fn main() {
    // Set version from git if available
    let version = if let Ok(output) = std::process::Command::new("git")
        .args(["describe", "--tags", "--always"])
        .output()
    {
        let git_version = String::from_utf8_lossy(&output.stdout);
        if !git_version.is_empty() {
            git_version.trim().to_string()
        } else {
            "0.1.0".to_string()
        }
    } else {
        "0.1.0".to_string()
    };

    println!("cargo:rustc-env=CARGO_PKG_VERSION={}", version);
}
