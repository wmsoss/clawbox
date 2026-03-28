mod commands;

use commands::detect;
use commands::docker;
use commands::env_config;
use commands::install;
use commands::system;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .invoke_handler(tauri::generate_handler![
            // detect
            detect::check_wsl2,
            detect::check_docker,
            detect::check_docker_running,
            detect::check_image,
            detect::check_code,
            detect::check_container,
            detect::check_path_issues,
            detect::check_all_env,
            // install
            install::handle_wsl2_install,
            install::handle_docker_install,
            install::start_docker_desktop,
            install::extract_code,
            install::load_image,
            install::pull_image,
            install::download_code,
            install::configure_docker_mirror,
            // docker
            docker::compose_up,
            docker::compose_down,
            docker::compose_restart,
            docker::wait_for_service,
            // env_config
            env_config::read_env,
            env_config::write_env,
            env_config::generate_jwt_secret,
            // system
            system::get_system_info,
            system::is_admin,
            system::run_as_admin,
            system::open_url,
            system::pick_directory,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
