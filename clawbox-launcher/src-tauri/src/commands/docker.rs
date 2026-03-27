use std::process::Command;
use serde::Serialize;

#[derive(Serialize)]
pub struct DockerResult {
    pub success: bool,
    pub message: String,
}

fn run_compose(compose_file: &str, work_dir: &str, args: &[&str]) -> DockerResult {
    let mut cmd = Command::new("docker");
    cmd.args(["compose", "-f", compose_file]);
    cmd.args(args);
    cmd.current_dir(work_dir);

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }

    match cmd.output() {
        Ok(o) if o.status.success() => DockerResult {
            success: true,
            message: String::from_utf8_lossy(&o.stdout).to_string(),
        },
        Ok(o) => DockerResult {
            success: false,
            message: String::from_utf8_lossy(&o.stderr).to_string(),
        },
        Err(e) => DockerResult {
            success: false,
            message: format!("执行失败: {}", e),
        },
    }
}

#[tauri::command]
pub fn compose_up(compose_file: &str, work_dir: &str) -> DockerResult {
    run_compose(compose_file, work_dir, &["up", "-d"])
}

#[tauri::command]
pub fn compose_down(compose_file: &str, work_dir: &str) -> DockerResult {
    run_compose(compose_file, work_dir, &["down"])
}

#[tauri::command]
pub fn compose_restart(compose_file: &str, work_dir: &str) -> DockerResult {
    run_compose(compose_file, work_dir, &["restart"])
}

#[tauri::command]
pub fn wait_for_service(url: &str, timeout_secs: u64) -> DockerResult {
    let start = std::time::Instant::now();
    let timeout = std::time::Duration::from_secs(timeout_secs);

    while start.elapsed() < timeout {
        // Simple TCP connect check
        if let Ok(url_parsed) = url::Url::parse(url) {
            if let Some(host) = url_parsed.host_str() {
                let port = url_parsed.port().unwrap_or(80);
                let addr = format!("{}:{}", host, port);
                if std::net::TcpStream::connect_timeout(
                    &addr.parse().unwrap_or_else(|_| {
                        std::net::SocketAddr::from(([127, 0, 0, 1], port))
                    }),
                    std::time::Duration::from_secs(2),
                )
                .is_ok()
                {
                    return DockerResult {
                        success: true,
                        message: format!(
                            "服务就绪（{}s）",
                            start.elapsed().as_secs()
                        ),
                    };
                }
            }
        }
        std::thread::sleep(std::time::Duration::from_secs(2));
    }

    DockerResult {
        success: false,
        message: format!("等待超时（{}s）", timeout_secs),
    }
}
