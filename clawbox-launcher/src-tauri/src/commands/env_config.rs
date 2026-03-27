use serde::Serialize;
use std::collections::HashMap;

#[derive(Serialize)]
pub struct EnvResult {
    pub success: bool,
    pub message: String,
    pub data: Option<HashMap<String, String>>,
}

#[tauri::command]
pub fn read_env(path: &str) -> EnvResult {
    let content = match std::fs::read_to_string(path) {
        Ok(c) => c,
        Err(e) => {
            return EnvResult {
                success: false,
                message: format!("无法读取 .env: {}", e),
                data: None,
            }
        }
    };

    let mut map = HashMap::new();
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if let Some((key, value)) = line.split_once('=') {
            map.insert(key.trim().to_string(), value.trim().to_string());
        }
    }

    EnvResult {
        success: true,
        message: format!("读取 {} 个配置项", map.len()),
        data: Some(map),
    }
}

#[tauri::command]
pub fn write_env(path: &str, data: HashMap<String, String>, template_path: &str) -> EnvResult {
    // 读取模板来保留注释结构
    let template = std::fs::read_to_string(template_path).unwrap_or_default();
    let mut output = Vec::new();
    let mut written_keys: std::collections::HashSet<String> =
        std::collections::HashSet::new();

    for line in template.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            output.push(line.to_string());
            continue;
        }
        if let Some((key, _)) = trimmed.split_once('=') {
            let key = key.trim();
            if let Some(value) = data.get(key) {
                output.push(format!("{}={}", key, value));
                written_keys.insert(key.to_string());
            } else {
                output.push(line.to_string());
            }
        } else {
            output.push(line.to_string());
        }
    }

    // 追加模板中没有的 key
    for (key, value) in &data {
        if !written_keys.contains(key) {
            output.push(format!("{}={}", key, value));
        }
    }

    match std::fs::write(path, output.join("\n") + "\n") {
        Ok(_) => EnvResult {
            success: true,
            message: ".env 已保存".to_string(),
            data: None,
        },
        Err(e) => EnvResult {
            success: false,
            message: format!("保存失败: {}", e),
            data: None,
        },
    }
}

#[tauri::command]
pub fn generate_jwt_secret() -> String {
    use rand::Rng;
    let mut rng = rand::thread_rng();
    (0..32)
        .map(|_| format!("{:02x}", rng.gen::<u8>()))
        .collect()
}
