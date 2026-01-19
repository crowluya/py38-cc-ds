use anyhow::{Context, Result};
use bollard::{
    Docker,
    api::ContainerCreateOptions,
    models::{ContainerConfig, HostConfig, Mount, MountTypeEnum, BindOptions}
};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;
use std::time::Duration;
use tracing::{info, error, debug};

const EXECUTION_TIMEOUT_SECS: u64 = 30;

pub struct DockerExecutor {
    docker: Docker,
}

impl DockerExecutor {
    pub fn new() -> Result<Self> {
        let docker = Docker::connect_with_local_defaults()
            .context("Failed to connect to Docker daemon")?;

        Ok(Self { docker })
    }

    pub async fn execute_code(
        &self,
        code: &str,
        language: &str,
        session_id: &str,
        mut output_tx: tokio::sync::mpsc::UnboundedSender<String>,
    ) -> Result<i32> {
        let image_name = self.get_image_for_language(language)?;
        let container_name = format!("code-exec-{}", session_id);

        info!("Executing {} code in container: {}", language, container_name);

        // Create temporary file with code
        let temp_file = self.create_temp_file(session_id, code, language)?;

        // Create and run container
        let config = self.build_container_config(&image_name, &temp_file, language)?;
        let options = Some(ContainerCreateOptions {
            name: Some(container_name.clone()),
            config: Some(config),
            host_config: Some(HostConfig {
                network_mode: Some("none".to_string()), // No network access
                mem_limit: Some(128 * 1024 * 1024), // 128MB memory limit
                cpu_quota: Some(100000),
                cpu_period: Some(100000),
                ..Default::default()
            }),
            ..Default::default()
        });

        // Create container
        self.docker
            .create_container(Some(options), None)
            .await
            .context("Failed to create container")?;

        // Start container
        self.docker
            .start_container::<String>(&container_name, None)
            .await
            .context("Failed to start container")?;

        // Wait for completion with timeout
        let timeout = Duration::from_secs(EXECUTION_TIMEOUT_SECS);
        let start_time = std::time::Instant::now();

        // Attach to container logs
        let mut logs = self.docker.logs::<String>(
            &container_name,
            Some(bollard::models::LogsOptions {
                follow: true,
                stdout: true,
                stderr: true,
                tail: "all".to_string(),
                ..Default::default()
            }),
        );

        // Stream logs
        use bollard::models::LogOutput;
        while let Some(log_result) = logs.next().await {
            match log_result {
                Ok(LogOutput::StdOut { message }) => {
                    let output = String::from_utf8_lossy(&message).to_string();
                    output_tx.send(output)?;
                }
                Ok(LogOutput::StdErr { message }) => {
                    let output = String::from_utf8_lossy(&message).to_string();
                    output_tx.send(output)?;
                }
                Err(e) => {
                    error!("Error reading logs: {:?}", e);
                }
                _ => {}
            }

            if start_time.elapsed() > timeout {
                error!("Execution timeout");
                break;
            }
        }

        // Wait for container to finish
        let exit_code = self.wait_for_container(&container_name, timeout).await?;

        // Cleanup container
        self.cleanup_container(&container_name).await?;

        // Cleanup temp file
        let _ = std::fs::remove_file(&temp_file);

        Ok(exit_code)
    }

    fn get_image_for_language(&self, language: &str) -> Result<String> {
        match language.to_lowercase().as_str() {
            "python" | "python3" => Ok("code-exec-python:latest".to_string()),
            "javascript" | "node" | "nodejs" => Ok("code-exec-node:latest".to_string()),
            "rust" => Ok("code-exec-rust:latest".to_string()),
            "go" => Ok("code-exec-go:latest".to_string()),
            _ => Err(anyhow::anyhow!("Unsupported language: {}", language)),
        }
    }

    fn create_temp_file(&self, session_id: &str, code: &str, language: &str) -> Result<String> {
        let extension = match language.to_lowercase().as_str() {
            "python" | "python3" => "py",
            "javascript" | "node" | "nodejs" => "js",
            "rust" => "rs",
            "go" => "go",
            _ => "txt",
        };

        let filename = format!("/tmp/code_{}_{}.{}", session_id, uuid::Uuid::new_v4(), extension);
        std::fs::write(&filename, code)?;
        Ok(filename)
    }

    fn build_container_config(&self, image: &str, code_file: &str, language: &str) -> Result<ContainerConfig> {
        let cmd = match language.to_lowercase().as_str() {
            "python" | "python3" => vec!["python".to_string(), code_file.to_string()],
            "javascript" | "node" | "nodejs" => vec!["node".to_string(), code_file.to_string()],
            "rust" => {
                // For Rust, we need to compile and run
                // This is simplified - in production, use a pre-built container with code mounted
                vec!["sh".to_string(), "-c".to_string(), format!("rustc {} -o /tmp/out && /tmp/out", code_file)]
            }
            "go" => vec!["go".to_string(), "run".to_string(), code_file.to_string()],
            _ => vec![code_file.to_string()],
        };

        Ok(ContainerConfig {
            image: Some(image.to_string()),
            cmd: Some(cmd),
            ..Default::default()
        })
    }

    async fn wait_for_container(&self, container_name: &str, timeout: Duration) -> Result<i32> {
        let start = std::time::Instant::now();

        loop {
            match self.docker.inspect_container::<String>(container_name, None).await {
                Ok(details) => {
                    if let Some(state) = details.state {
                        if let Some(status) = state.status {
                            if status == "exited" {
                                return Ok(state.exit_code.unwrap_or(-1));
                            }
                        }
                    }
                }
                Err(e) => {
                    error!("Error inspecting container: {:?}", e);
                }
            }

            if start.elapsed() > timeout {
                // Kill container on timeout
                let _ = self.docker.kill_container::<String>(container_name, None).await;
                return Ok(-1); // Timeout exit code
            }

            tokio::time::sleep(Duration::from_millis(100)).await;
        }
    }

    async fn cleanup_container(&self, container_name: &str) -> Result<()> {
        // Remove container (force if running)
        let _ = self.docker
            .remove_container(container_name, None)
            .await;

        Ok(())
    }
}

impl Default for DockerExecutor {
    fn default() -> Self {
        Self::new().expect("Failed to create DockerExecutor")
    }
}
