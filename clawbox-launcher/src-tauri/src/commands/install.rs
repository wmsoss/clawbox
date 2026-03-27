use std::process::Command;
use serde::Serialize;

#[derive(Serialize)]
pub struct InstallResult {
    pub success: bool,
    pub message: String,
}

/// WSL2 installation (Windows only).
/// Opens UAC prompt and runs `wsl --install`.
#[tauri::command]
pub fn handle_wsl2_install() -> InstallResult {
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;

        let result = Command::new("powershell")
            .args([
                "-Command",
                "Start-Process wsl.exe -ArgumentList '--install --no-distribution' -Verb RunAs -Wait",
            ])
            .creation_flags(CREATE_NO_WINDOW)
            .output();

        match result {
            Ok(o) if o.status.success() => InstallResult {
                success: true,
                message: "WSL2 安装已启动，可能需要重启电脑".to_string(),
            },
            Ok(o) => InstallResult {
                success: false,
                message: format!(
                    "WSL2 安装失败: {}",
                    String::from_utf8_lossy(&o.stderr)
                ),
            },
            Err(e) => InstallResult {
                success: false,
                message: format!("执行失败: {}", e),
            },
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        InstallResult {
            success: true,
            message: "当前系统无需安装 WSL2".to_string(),
        }
    }
}

/// Docker installation — platform-specific guidance + auto-open download page.
#[tauri::command]
pub fn handle_docker_install() -> InstallResult {
    #[cfg(target_os = "windows")]
    {
        let _ = open::that("https://www.docker.com/products/docker-desktop/");
        return InstallResult {
            success: true,
            message: "已打开 Docker Desktop 下载页面".to_string(),
        };
    }
    #[cfg(target_os = "macos")]
    {
        let _ = open::that("https://orbstack.dev/download");
        return InstallResult {
            success: true,
            message: "已打开 OrbStack 下载页面（推荐 macOS 使用，已有 Docker Desktop 也兼容）".to_string(),
        };
    }
    #[cfg(target_os = "linux")]
    {
        let _ = open::that("https://docs.docker.com/engine/install/");
        return InstallResult {
            success: true,
            message: "已打开 Docker Engine 安装文档\n安装命令: curl -fsSL https://get.docker.com | sh".to_string(),
        };
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos", target_os = "linux")))]
    {
        return InstallResult {
            success: true,
            message: "https://docs.docker.com/get-docker/".to_string(),
        };
    }
}

/// Start Docker runtime — tries OrbStack first on macOS, Docker Desktop on Windows.
#[tauri::command]
pub fn start_docker_desktop() -> InstallResult {
    #[cfg(target_os = "windows")]
    {
        let paths = [
            format!(
                "{}\\Docker\\Docker\\Docker Desktop.exe",
                std::env::var("ProgramFiles").unwrap_or_default()
            ),
            format!(
                "{}\\Docker\\Docker Desktop.exe",
                std::env::var("LOCALAPPDATA").unwrap_or_default()
            ),
        ];

        for p in &paths {
            if std::path::Path::new(p).exists() {
                match Command::new(p).spawn() {
                    Ok(_) => {
                        return InstallResult {
                            success: true,
                            message: "Docker Desktop 启动中...".to_string(),
                        }
                    }
                    Err(e) => {
                        return InstallResult {
                            success: false,
                            message: format!("启动失败: {}", e),
                        }
                    }
                }
            }
        }

        return InstallResult {
            success: false,
            message: "未找到 Docker Desktop".to_string(),
        };
    }

    #[cfg(target_os = "macos")]
    {
        // Try OrbStack first, then Docker Desktop
        if let Ok(o) = Command::new("open").args(["-a", "OrbStack"]).output() {
            if o.status.success() {
                return InstallResult {
                    success: true,
                    message: "OrbStack 启动中...".to_string(),
                };
            }
        }
        // Fallback to Docker Desktop
        let _ = Command::new("open").args(["-a", "Docker"]).spawn();
        return InstallResult {
            success: true,
            message: "Docker Desktop 启动中...".to_string(),
        };
    }

    #[cfg(target_os = "linux")]
    {
        let result = Command::new("systemctl")
            .args(["start", "docker"])
            .output();
        return match result {
            Ok(o) if o.status.success() => InstallResult {
                success: true,
                message: "Docker Engine 已启动".to_string(),
            },
            _ => InstallResult {
                success: false,
                message: "请执行: sudo systemctl start docker".to_string(),
            },
        };
    }
}

#[tauri::command]
pub fn extract_code(zip_path: &str, target_dir: &str) -> InstallResult {
    let file = match std::fs::File::open(zip_path) {
        Ok(f) => f,
        Err(e) => {
            return InstallResult {
                success: false,
                message: format!("无法打开代码包: {}", e),
            }
        }
    };

    let mut archive = match zip::ZipArchive::new(file) {
        Ok(a) => a,
        Err(e) => {
            return InstallResult {
                success: false,
                message: format!("ZIP 解析失败: {}", e),
            }
        }
    };

    match archive.extract(target_dir) {
        Ok(_) => InstallResult {
            success: true,
            message: "代码解压完成".to_string(),
        },
        Err(e) => InstallResult {
            success: false,
            message: format!("解压失败: {}", e),
        },
    }
}

#[tauri::command]
pub fn load_image(tar_path: &str) -> InstallResult {
    let file = match std::fs::File::open(tar_path) {
        Ok(f) => f,
        Err(e) => {
            return InstallResult {
                success: false,
                message: format!("镜像文件不存在: {}", e),
            }
        }
    };

    match Command::new("docker")
        .arg("load")
        .stdin(file)
        .output()
    {
        Ok(o) if o.status.success() => InstallResult {
            success: true,
            message: "镜像加载成功".to_string(),
        },
        Ok(o) => InstallResult {
            success: false,
            message: format!("加载失败: {}", String::from_utf8_lossy(&o.stderr)),
        },
        Err(e) => InstallResult {
            success: false,
            message: format!("执行失败: {}", e),
        },
    }
}

/// Smart image pull — try China mirror first (Alibaba ACR), fallback to DockerHub.
#[tauri::command]
pub async fn pull_image(image_name: String) -> InstallResult {
    // Auto-configure mirror accelerator for faster pulls in China
    let _ = configure_docker_mirror("https://docker.1ms.run");

    // Image sources: DockerHub primary (with mirror acceleration), ACR backup
    let sources = [
        ("womso/clawbox:latest", "DockerHub"),
        ("crpi-8rb3058vq4kbngw1.cn-shanghai.personal.cr.aliyuncs.com/womso/clawbox:latest", "阿里云 ACR"),
    ];

    for (source, label) in &sources {
        let result = tokio::process::Command::new("docker")
            .args(["pull", source])
            .output()
            .await;

        match result {
            Ok(o) if o.status.success() => {
                // Tag as the canonical local name
                let _ = tokio::process::Command::new("docker")
                    .args(["tag", source, &image_name])
                    .output()
                    .await;

                return InstallResult {
                    success: true,
                    message: format!("镜像拉取成功 ({})", label),
                };
            }
            Ok(o) => {
                let stderr = String::from_utf8_lossy(&o.stderr);
                eprintln!("[pull_image] {} failed: {}", label, stderr);
                // Continue to next source
            }
            Err(e) => {
                eprintln!("[pull_image] {} error: {}", label, e);
            }
        }
    }

    InstallResult {
        success: false,
        message: "所有镜像源拉取失败，请检查网络连接".to_string(),
    }
}

/// Download code from GitHub public repo (no auth needed).
/// Tries ghgo.xyz proxy first for China users, falls back to raw GitHub.
#[tauri::command]
pub async fn download_code(target_dir: String, repo: String) -> InstallResult {
    let urls = [
        format!("https://ghgo.xyz/https://github.com/{}/archive/refs/heads/main.zip", repo),
        format!("https://github.com/{}/archive/refs/heads/main.zip", repo),
    ];

    let client = match reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(120))
        .build()
    {
        Ok(c) => c,
        Err(e) => return InstallResult {
            success: false,
            message: format!("HTTP 客户端创建失败: {}", e),
        },
    };

    let mut last_err = String::new();

    for url in &urls {
        match client.get(url).send().await {
            Ok(resp) if resp.status().is_success() => {
                match resp.bytes().await {
                    Ok(bytes) => {
                        // Write to temp file
                        let tmp = std::env::temp_dir().join("clawbox-code.zip");
                        if let Err(e) = std::fs::write(&tmp, &bytes) {
                            return InstallResult {
                                success: false,
                                message: format!("写入临时文件失败: {}", e),
                            };
                        }

                        // Extract zip
                        let file = match std::fs::File::open(&tmp) {
                            Ok(f) => f,
                            Err(e) => return InstallResult {
                                success: false,
                                message: format!("打开 zip 失败: {}", e),
                            },
                        };

                        let mut archive = match zip::ZipArchive::new(file) {
                            Ok(a) => a,
                            Err(e) => return InstallResult {
                                success: false,
                                message: format!("ZIP 解析失败: {}", e),
                            },
                        };

                        // GitHub zips contain a top-level dir like "clawbox-main/"
                        // Extract to temp dir first, then move contents
                        let extract_tmp = std::env::temp_dir().join("clawbox-extract");
                        let _ = std::fs::remove_dir_all(&extract_tmp);
                        let _ = std::fs::create_dir_all(&extract_tmp);

                        if let Err(e) = archive.extract(&extract_tmp) {
                            return InstallResult {
                                success: false,
                                message: format!("解压失败: {}", e),
                            };
                        }

                        // Find the top-level directory inside the extracted zip
                        let entries: Vec<_> = std::fs::read_dir(&extract_tmp)
                            .map(|rd| rd.filter_map(|e| e.ok()).collect())
                            .unwrap_or_default();

                        let source_dir = if entries.len() == 1 && entries[0].path().is_dir() {
                            entries[0].path()
                        } else {
                            extract_tmp.clone()
                        };

                        // Create target dir
                        let target = std::path::Path::new(&target_dir);
                        let _ = std::fs::create_dir_all(target);

                        // Copy contents from source to target
                        if let Err(e) = copy_dir_contents(&source_dir, target) {
                            return InstallResult {
                                success: false,
                                message: format!("复制文件失败: {}", e),
                            };
                        }

                        // Cleanup
                        let _ = std::fs::remove_file(&tmp);
                        let _ = std::fs::remove_dir_all(&extract_tmp);

                        return InstallResult {
                            success: true,
                            message: format!("代码下载并解压完成 ({:.1} MB)", bytes.len() as f64 / 1_048_576.0),
                        };
                    }
                    Err(e) => {
                        last_err = format!("下载失败: {}", e);
                    }
                }
            }
            Ok(resp) => {
                last_err = format!("HTTP {}", resp.status());
            }
            Err(e) => {
                last_err = format!("连接失败: {}", e);
            }
        }
    }

    InstallResult {
        success: false,
        message: format!("代码下载失败: {}", last_err),
    }
}

/// Recursively copy directory contents.
fn copy_dir_contents(src: &std::path::Path, dst: &std::path::Path) -> std::io::Result<()> {
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());

        if src_path.is_dir() {
            std::fs::create_dir_all(&dst_path)?;
            copy_dir_contents(&src_path, &dst_path)?;
        } else {
            std::fs::copy(&src_path, &dst_path)?;
        }
    }
    Ok(())
}

/// Configure Docker registry mirror in daemon.json.
#[tauri::command]
pub fn configure_docker_mirror(mirror_url: &str) -> InstallResult {
    let daemon_json_path = get_daemon_json_path();

    // Read existing daemon.json or create new
    let mut config: serde_json::Value = if let Ok(content) = std::fs::read_to_string(&daemon_json_path) {
        serde_json::from_str(&content).unwrap_or(serde_json::json!({}))
    } else {
        serde_json::json!({})
    };

    // Check if mirror already configured
    if let Some(mirrors) = config.get("registry-mirrors").and_then(|m| m.as_array()) {
        if mirrors.iter().any(|m| m.as_str() == Some(mirror_url)) {
            return InstallResult {
                success: true,
                message: "镜像加速器已配置".to_string(),
            };
        }
    }

    // Add mirror
    let mirrors = config
        .as_object_mut()
        .unwrap()
        .entry("registry-mirrors")
        .or_insert(serde_json::json!([]));

    if let Some(arr) = mirrors.as_array_mut() {
        arr.push(serde_json::json!(mirror_url));
    }

    // Ensure parent directory exists
    if let Some(parent) = std::path::Path::new(&daemon_json_path).parent() {
        let _ = std::fs::create_dir_all(parent);
    }

    // Write back
    match std::fs::write(&daemon_json_path, serde_json::to_string_pretty(&config).unwrap_or_default()) {
        Ok(_) => InstallResult {
            success: true,
            message: format!("镜像加速器已配置到 {}，需要重启 Docker 生效", daemon_json_path),
        },
        Err(e) => InstallResult {
            success: false,
            message: format!("写入 daemon.json 失败: {}", e),
        },
    }
}

fn get_daemon_json_path() -> String {
    #[cfg(target_os = "windows")]
    {
        let home = std::env::var("USERPROFILE").unwrap_or_else(|_| ".".to_string());
        format!("{}\\.docker\\daemon.json", home)
    }
    #[cfg(target_os = "macos")]
    {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        format!("{}/.docker/daemon.json", home)
    }
    #[cfg(target_os = "linux")]
    {
        "/etc/docker/daemon.json".to_string()
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos", target_os = "linux")))]
    {
        "daemon.json".to_string()
    }
}

