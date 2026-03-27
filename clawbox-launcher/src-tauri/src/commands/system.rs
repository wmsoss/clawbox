use serde::Serialize;

#[derive(Serialize)]
pub struct SystemInfo {
    pub is_admin: bool,
    pub os: String,
    pub arch: String,
}

#[tauri::command]
pub fn get_system_info() -> SystemInfo {
    SystemInfo {
        is_admin: is_admin(),
        os: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
    }
}

#[tauri::command]
pub fn is_admin() -> bool {
    #[cfg(target_os = "windows")]
    {
        // Check via `net session` — succeeds only if admin
        std::process::Command::new("net")
            .arg("session")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
    #[cfg(not(target_os = "windows"))]
    {
        // Unix: check if running as root via `id -u`
        std::process::Command::new("id")
            .arg("-u")
            .output()
            .map(|o| String::from_utf8_lossy(&o.stdout).trim() == "0")
            .unwrap_or(false)
    }
}

#[tauri::command]
pub fn run_as_admin() -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        let exe = std::env::current_exe().map_err(|e| e.to_string())?;
        std::process::Command::new("powershell")
            .args([
                "-Command",
                &format!(
                    "Start-Process '{}' -Verb RunAs",
                    exe.to_string_lossy()
                ),
            ])
            .spawn()
            .map_err(|e| format!("提权失败: {}", e))?;
        std::process::exit(0);
    }
    #[cfg(not(target_os = "windows"))]
    {
        Err("请使用 sudo 重新运行".to_string())
    }
}

#[tauri::command]
pub fn open_url(url: &str) -> Result<(), String> {
    open::that(url).map_err(|e| format!("打开失败: {}", e))
}

#[tauri::command]
pub fn pick_directory() -> Option<String> {
    rfd::FileDialog::new()
        .set_title("选择安装目录")
        .pick_folder()
        .map(|p| p.to_string_lossy().to_string())
}
