import { useState } from "react";
import { CheckCircle2, XCircle, Loader2, RefreshCw, ShieldAlert, ShieldCheck, Download, CloudDownload, FolderSearch, FolderOpen } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import type { EnvStatus, SystemInfo, ActionResult } from "../types";

interface Props {
  env: EnvStatus | null;
  systemInfo: SystemInfo | null;
  loading: boolean;
  status: string;
  installDir: string;
  setInstallDir: (dir: string) => void;
  onCheckEnv: () => void;
  addLog: (msg: string) => void;
}

export default function PhaseEnvCheck({ env, systemInfo, loading, status, installDir, setInstallDir, onCheckEnv, addLog }: Props) {

  async function handleAction(action: string, args: Record<string, unknown> = {}, label?: string) {
    const confirmMsg = label ? `确认执行「${label}」操作？` : `确认执行 ${action}？`;
    if (!window.confirm(confirmMsg)) {
      addLog("用户取消操作");
      return;
    }
    addLog(`执行: ${label || action}...`);
    try {
      const result = await invoke<ActionResult>(action, args);
      addLog(result.message);
      if (result.success) setTimeout(onCheckEnv, 2000);
    } catch (e) {
      addLog(`失败: ${e}`);
    }
  }

  async function handlePullImage() {
    if (!window.confirm("确认从 DockerHub 拉取 Clawbox 镜像？\n将自动配置国内加速器。")) {
      addLog("用户取消镜像拉取");
      return;
    }
    addLog("开始拉取镜像（DockerHub + 加速器）...");
    try {
      const result = await invoke<ActionResult>("pull_image", {
        imageName: "clawbox-image:latest",
      });
      addLog(result.message);
      if (result.success) setTimeout(onCheckEnv, 2000);
    } catch (e) {
      addLog(`镜像拉取失败: ${e}`);
    }
  }

  async function handleDownloadCode() {
    if (!installDir || installDir === "~/clawbox") {
      window.alert("请先设置安装目录！");
      return;
    }
    if (!window.confirm(`确认从 GitHub 下载项目代码到:\n${installDir}`)) {
      addLog("用户取消代码下载");
      return;
    }
    addLog(`开始下载代码到 ${installDir}...`);
    try {
      const result = await invoke<ActionResult>("download_code", {
        targetDir: installDir,
        repo: "wmsoss/clawbox",
      });
      addLog(result.message);
      if (result.success) setTimeout(onCheckEnv, 2000);
    } catch (e) {
      addLog(`代码下载失败: ${e}`);
    }
  }

  async function pickInstallDir() {
    try {
      const selected = await invoke<string | null>("pick_directory");
      if (selected) {
        setInstallDir(selected);
        addLog(`安装目录设为: ${selected}`);
        // Re-check env with new dir
        setTimeout(onCheckEnv, 500);
      }
    } catch (e) {
      addLog(`选择目录失败: ${e}`);
    }
  }

  const envItems = [
    {
      label: "WSL2",
      ok: env?.wsl2 ?? false,
      status: env ? (env.wsl2 ? "已安装" : "未安装") : "待检测",
      action: "handle_wsl2_install",
      btnText: "安装",
      icon: "install" as const,
      hide: systemInfo?.os !== "windows",
    },
    {
      label: systemInfo?.os === "windows" ? "Docker Desktop" :
             systemInfo?.os === "linux" ? "Docker Engine" : "Docker",
      ok: env?.docker_running ?? false,
      status: env
        ? env.docker_installed
          ? env.docker_running ? "已启动" : "未启动"
          : "未安装"
        : "待检测",
      action: env?.docker_installed ? "start_docker_desktop" : "handle_docker_install",
      btnText: env?.docker_installed ? "启动" : "安装",
      icon: "install" as const,
    },
    {
      label: "镜像",
      ok: env?.image_loaded ?? false,
      status: env ? (env.image_loaded ? "已就绪" : "未拉取") : "待检测",
      action: "__pull_image__",
      btnText: "拉取",
      icon: "cloud" as const,
    },
    {
      label: "代码",
      ok: env?.code_extracted ?? false,
      status: env ? (env.code_extracted ? "已就绪" : "未下载") : "待检测",
      action: "__download_code__",
      btnText: "下载",
      icon: "download" as const,
    },
  ];

  function handleItemAction(item: typeof envItems[0]) {
    if (item.action === "__pull_image__") {
      handlePullImage();
    } else if (item.action === "__download_code__") {
      handleDownloadCode();
    } else {
      handleAction(item.action, {}, `${item.btnText} ${item.label}`);
    }
  }

  return (
    <div className="phase-content">
      {/* Admin Warning */}
      {systemInfo && !systemInfo.is_admin && systemInfo.os === "windows" && (
        <div className="warning-bar">
          <ShieldAlert size={16} />
          <span>未以管理员身份运行，部分功能可能受限</span>
          <button className="neu-btn neu-btn-sm" onClick={() => invoke("run_as_admin")}>
            <ShieldCheck size={13} /> 提权重启
          </button>
        </div>
      )}

      <div className="phase-title">🔍 环境检测</div>
      <p className="phase-desc">正在检查运行环境，确保所有必要组件已就绪。</p>

      {/* Install Directory — FIRST, before env cards */}
      <div className="neu-card" style={{ padding: "12px 16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <FolderSearch size={14} />
          <span style={{ fontSize: 13, fontWeight: 600, whiteSpace: "nowrap" }}>安装目录</span>
          <input
            className="neu-input"
            style={{ flex: 1, padding: "6px 10px", fontSize: 12 }}
            value={installDir}
            onChange={(e) => setInstallDir(e.target.value)}
            placeholder="选择项目安装目录"
          />
          <button className="neu-btn neu-btn-sm" onClick={pickInstallDir}>
            <FolderOpen size={12} /> 选择
          </button>
        </div>
        <div style={{ fontSize: 11, color: "var(--text3)", marginTop: 4, paddingLeft: 22 }}>
          代码将下载到此目录，docker compose 也在此目录运行
        </div>
      </div>

      {/* Environment Cards */}
      <div className="neu-card">
        <div className="env-grid">
          {envItems
            .filter((item) => !item.hide)
            .map((item) => (
              <div key={item.label} className="neu-card-inset env-item">
                {env ? (
                  item.ok ? (
                    <CheckCircle2 size={16} color="var(--green)" />
                  ) : (
                    <XCircle size={16} color="var(--red)" />
                  )
                ) : (
                  <Loader2 size={16} className="spin" />
                )}
                <div className="env-item-info">
                  <div className="env-item-title">{item.label}</div>
                  <div className="env-item-status">{item.status}</div>
                </div>
                {!item.ok && (
                  <button
                    className="neu-btn neu-btn-sm"
                    onClick={() => handleItemAction(item)}
                  >
                    {item.icon === "cloud" && <CloudDownload size={12} />}
                    {item.icon === "download" && <Download size={12} />}
                    {" "}{item.btnText}
                  </button>
                )}
              </div>
            ))}
        </div>
      </div>

      {/* Status Bar */}
      <div className="neu-card" style={{ padding: "10px 16px" }}>
        <div className="status-bar">
          <span className="status-text">{status}</span>
          <div className="progress-bar">
            {loading ? (
              <div className="progress-bar-indeterminate" />
            ) : (
              <div className="progress-bar-fill" style={{ width: "100%" }} />
            )}
          </div>
          <button className="neu-btn neu-btn-sm" onClick={onCheckEnv} disabled={loading}>
            <RefreshCw size={12} /> 检测
          </button>
        </div>
      </div>
    </div>
  );
}
