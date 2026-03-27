use std::process::Command;
use serde::Serialize;

#[derive(Serialize)]
pub struct EnvStatus {
    pub wsl2: bool,
    pub docker_installed: bool,
    pub docker_running: bool,
    pub image_loaded: bool,
    pub code_extracted: bool,
    pub container_running: bool,
    pub path_issues: Vec<String>,
}

#[tauri::command]
pub fn check_wsl2() -> bool {
    #[cfg(target_os = "windows")]
    {
        Command::new("wsl")
            .args(["--list", "--verbose"])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
    #[cfg(not(target_os = "windows"))]
    {
        true // WSL2 不适用于 Mac/Linux
    }
}

#[tauri::command]
pub fn check_docker() -> bool {
    Command::new("docker")
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

#[tauri::command]
pub fn check_docker_running() -> bool {
    Command::new("docker")
        .arg("info")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

#[tauri::command]
pub fn check_image(image_name: &str) -> bool {
    Command::new("docker")
        .args(["images", "-q", image_name])
        .output()
        .map(|o| o.status.success() && !o.stdout.is_empty())
        .unwrap_or(false)
}

#[tauri::command]
pub fn check_code(install_dir: &str) -> bool {
    let base = std::path::Path::new(install_dir);
    let required_files = [
        "docker-compose.yml",
        "scripts/start.sh",
        "docker/supervisord.conf",
    ];
    let required_dirs = ["backend", "frontend"];

    required_files.iter().all(|f| base.join(f).is_file())
        && required_dirs.iter().all(|d| base.join(d).is_dir())
}

#[tauri::command]
pub fn check_container(container_name: &str) -> bool {
    Command::new("docker")
        .args([
            "ps",
            "--filter",
            &format!("name={}", container_name),
            "--format",
            "{{.Status}}",
        ])
        .output()
        .map(|o| {
            let stdout = String::from_utf8_lossy(&o.stdout);
            o.status.success() && stdout.contains("Up")
        })
        .unwrap_or(false)
}

#[tauri::command]
pub fn check_path_issues(path: &str) -> Vec<String> {
    let mut issues = Vec::new();
    if path.chars().any(|c| c >= '\u{4e00}' && c <= '\u{9fff}') {
        issues.push("路径含中文".to_string());
    }
    if path.contains(' ') {
        issues.push("路径含空格".to_string());
    }
    issues
}

#[tauri::command]
pub fn check_all_env(install_dir: &str, image_name: &str, container_name: &str) -> EnvStatus {
    let wsl2 = check_wsl2();
    let docker_installed = check_docker();
    let docker_running = if docker_installed {
        check_docker_running()
    } else {
        false
    };
    let image_loaded = if docker_running {
        check_image(image_name)
    } else {
        false
    };
    let code_extracted = check_code(install_dir);
    let container_running = if docker_running {
        check_container(container_name)
    } else {
        false
    };
    let path_issues = check_path_issues(install_dir);

    EnvStatus {
        wsl2,
        docker_installed,
        docker_running,
        image_loaded,
        code_extracted,
        container_running,
        path_issues,
    }
}
