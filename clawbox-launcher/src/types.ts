export interface EnvStatus {
  wsl2: boolean;
  docker_installed: boolean;
  docker_running: boolean;
  image_loaded: boolean;
  code_extracted: boolean;
  container_running: boolean;
  path_issues: string[];
}

export interface ActionResult {
  success: boolean;
  message: string;
}

export interface SystemInfo {
  is_admin: boolean;
  os: string;
  arch: string;
}

export interface EnvData {
  [key: string]: string;
}
