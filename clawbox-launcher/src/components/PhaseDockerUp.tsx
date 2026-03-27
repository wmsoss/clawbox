import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Rocket, Loader2, MonitorCheck } from "lucide-react";
import type { ActionResult } from "../types";

interface Props {
  installDir: string;
  addLog: (msg: string) => void;
  onReady: (isFirstRun: boolean) => void;
}

export default function PhaseDockerUp({ installDir, addLog, onReady }: Props) {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("检测容器状态...");
  const [containerRunning, setContainerRunning] = useState<boolean | null>(null);

  // On mount, check if container is already running
  useEffect(() => {
    checkContainerStatus();
  }, []);

  async function checkContainerStatus() {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/health");
      if (res.ok) {
        setContainerRunning(true);
        setStatusText("容器已在运行");
        addLog("检测到容器已在运行");
      } else {
        setContainerRunning(false);
        setStatusText("准备启动容器...");
      }
    } catch {
      setContainerRunning(false);
      setStatusText("准备启动容器...");
    }
  }

  async function checkIsFirstRun(): Promise<boolean> {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/setup/state");
      if (res.ok) {
        const data = await res.json();
        // If setup has progressed past step 0, it's not first run
        return !data.is_completed && (data.current_step || 0) === 0;
      }
    } catch {
      // API not ready, assume first run
    }
    return true;
  }

  async function startContainer() {
    setRunning(true);
    setProgress(10);
    setStatusText("启动 docker compose...");
    addLog(`启动 Clawbox 容器 (目录: ${installDir})...`);

    try {
      // Step 1: docker compose up (idempotent — safe if already running)
      setProgress(20);
      const result = await invoke<ActionResult>("compose_up", {
        composeFile: "docker-compose.yml",
        workDir: installDir,
      });
      addLog(result.message);

      if (!result.success) {
        setStatusText("容器启动失败");
        setRunning(false);
        return;
      }

      // Step 2: Wait for service healthy
      setProgress(60);
      setStatusText("等待服务就绪...");
      addLog("等待 HTTP 服务就绪...");

      const ready = await invoke<ActionResult>("wait_for_service", {
        url: "http://127.0.0.1:8000",
        timeoutSecs: 60,
      });
      addLog(ready.message);

      if (!ready.success) {
        setStatusText("服务启动超时，请检查日志");
        setRunning(false);
        return;
      }

      await proceedAfterReady();
    } catch (e) {
      addLog(`启动失败: ${e}`);
      setStatusText("启动失败");
      setRunning(false);
    }
  }

  async function proceedAfterReady() {
    setProgress(90);
    setStatusText("检查初始化状态...");

    const isFirstRun = await checkIsFirstRun();

    setProgress(100);
    setStatusText(isFirstRun ? "容器就绪，进入安装向导..." : "容器就绪，进入控制台...");
    addLog(isFirstRun ? "首次启动，进入安装向导" : "已初始化，进入控制台");

    setTimeout(() => onReady(isFirstRun), 500);
  }

  async function enterDirectly() {
    setRunning(true);
    setProgress(50);
    addLog("容器已在运行，检查初始化状态...");
    await proceedAfterReady();
  }

  return (
    <div className="phase-content">
      <div className="phase-title">🚀 启动容器</div>
      <p className="phase-desc">启动 Docker 容器并等待服务就绪。</p>

      <div className="neu-card" style={{ padding: "24px", textAlign: "center" }}>
        {containerRunning === null ? (
          // Still checking
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
            <Loader2 size={20} className="spin" />
            <span style={{ fontSize: 14 }}>检测容器状态...</span>
          </div>
        ) : containerRunning && !running ? (
          // Container already running — offer direct entry
          <>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 16 }}>
              <MonitorCheck size={20} color="var(--green)" />
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--green)" }}>容器已在运行</span>
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
              <button className="neu-btn neu-btn-primary" style={{ height: 44, fontSize: 14, padding: "0 24px" }} onClick={enterDirectly}>
                <Rocket size={16} /> 进入控制台
              </button>
              <button className="neu-btn" style={{ height: 44, fontSize: 14, padding: "0 24px" }} onClick={startContainer}>
                <Rocket size={16} /> 重新启动
              </button>
            </div>
          </>
        ) : !running ? (
          // Not running — offer start
          <>
            <p style={{ fontSize: 14, color: "var(--text2)", marginBottom: 20 }}>
              环境已就绪，点击下方按钮启动 Clawbox 容器。
            </p>
            <button className="neu-btn neu-btn-primary" style={{ height: 48, fontSize: 15, padding: "0 32px" }} onClick={startContainer}>
              <Rocket size={18} /> 启动 Clawbox
            </button>
          </>
        ) : (
          // Running/in-progress
          <>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 10, marginBottom: 16 }}>
              {progress < 100 ? <Loader2 size={20} className="spin" /> : <Rocket size={20} color="var(--green)" />}
              <span style={{ fontSize: 14, fontWeight: 600 }}>{statusText}</span>
            </div>
            <div className="progress-bar" style={{ height: 8, borderRadius: 4 }}>
              <div
                className="progress-bar-fill"
                style={{ width: `${progress}%`, transition: "width 0.5s ease" }}
              />
            </div>
            <div style={{ fontSize: 12, color: "var(--text3)", marginTop: 8 }}>{progress}%</div>
          </>
        )}
      </div>
    </div>
  );
}
