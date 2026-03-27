import { useState, useEffect, useRef, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Moon, Sun, RefreshCw } from "lucide-react";
import "./styles/neumorphism.css";
import type { EnvStatus, SystemInfo } from "./types";

import PhaseEnvCheck from "./components/PhaseEnvCheck";
import PhaseEnvConfig from "./components/PhaseEnvConfig";
import PhaseDockerUp from "./components/PhaseDockerUp";
import WizardStep0Admin from "./components/WizardStep0Admin";
import WizardStep1Network from "./components/WizardStep1Network";
import WizardStep2LLM from "./components/WizardStep2LLM";
import WizardStep3Finish from "./components/WizardStep3Finish";
import PhaseDashboard from "./components/PhaseDashboard";

type Phase = "env-check" | "env-config" | "docker-up" | "wizard" | "dashboard";

const PHASE_LABELS: Record<Phase, string> = {
  "env-check": "环境检测",
  "env-config": "环境配置",
  "docker-up": "启动容器",
  "wizard": "安装向导",
  "dashboard": "控制台",
};

const PHASE_ORDER: Phase[] = ["env-check", "env-config", "docker-up", "wizard", "dashboard"];

function App() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [phase, setPhaseState] = useState<Phase>(() => {
    return (localStorage.getItem("clawbox_phase") as Phase) || "env-check";
  });
  const [wizardStep, setWizardStepState] = useState(() => {
    return parseInt(localStorage.getItem("clawbox_wizard_step") || "0", 10);
  });
  const [authToken, setAuthToken] = useState("");

  const setPhase = useCallback((p: Phase) => {
    setPhaseState(p);
    localStorage.setItem("clawbox_phase", p);
  }, []);
  const setWizardStep = useCallback((s: number | ((prev: number) => number)) => {
    setWizardStepState((prev) => {
      const next = typeof s === "function" ? s(prev) : s;
      localStorage.setItem("clawbox_wizard_step", String(next));
      return next;
    });
  }, []);

  // Shared state
  const [env, setEnv] = useState<EnvStatus | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [status, setStatus] = useState("正在检测环境...");
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState<string[]>([]);
  const logRef = useRef<HTMLDivElement>(null);
  const scanningRef = useRef(false);
  const [installDir, setInstallDirState] = useState(() => {
    return localStorage.getItem("clawbox_install_dir") || "~/clawbox";
  });

  const setInstallDir = useCallback((dir: string) => {
    setInstallDirState(dir);
    localStorage.setItem("clawbox_install_dir", dir);
  }, []);

  const addLog = useCallback((msg: string) => {
    const ts = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    setLogs((prev) => [...prev, `[${ts}] ${msg}`]);
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const initialPhaseRef = useRef(phase);

  useEffect(() => {
    invoke<SystemInfo>("get_system_info").then(setSystemInfo).catch(() => {});
    // Only run env check on startup if we're at env-check phase
    if (initialPhaseRef.current === "env-check") {
      checkEnv();
    }
  }, []);

  // Re-check env when installDir changes
  useEffect(() => {
    if (installDir && installDir !== "~/clawbox") {
      const timer = setTimeout(() => checkEnv(), 300);
      return () => clearTimeout(timer);
    }
  }, [installDir]);

  async function checkEnv() {
    if (scanningRef.current) return;
    scanningRef.current = true;
    setLoading(true);
    setStatus("正在检测环境...");
    addLog("开始环境检测...");

    try {
      const result = await invoke<EnvStatus>("check_all_env", {
        installDir: installDir,
        imageName: "clawbox-image:latest",
        containerName: "clawbox",
      });
      setEnv(result);

      const allOk =
        (result.wsl2 || systemInfo?.os !== "windows") &&
        result.docker_running &&
        result.image_loaded &&
        result.code_extracted;

      if (!result.wsl2 && systemInfo?.os === "windows") {
        setStatus("请先安装 WSL2");
      } else if (!result.docker_installed) {
        setStatus("请先安装 Docker");
      } else if (!result.docker_running) {
        setStatus("请启动 Docker");
        addLog("Docker 已安装但未运行，尝试启动...");
        const startResult = await invoke<{ success: boolean; message: string }>("start_docker_desktop");
        addLog(startResult.message);
        if (startResult.success) {
          scanningRef.current = false;
          setTimeout(checkEnv, 5000);
          return;
        }
      } else if (allOk) {
        setStatus("环境就绪");
      } else {
        setStatus("正在准备环境...");
      }

      if (result.path_issues.length > 0) {
        addLog(`⚠ 路径问题: ${result.path_issues.join(", ")}`);
      }
      addLog("环境检测完成");
    } catch (e) {
      addLog(`环境检测失败: ${e}`);
      setStatus("检测失败");
    }

    setLoading(false);
    scanningRef.current = false;
  }

  // Check if all env requirements are met for auto-advance
  const allReady =
    env &&
    (env.wsl2 || systemInfo?.os !== "windows") &&
    env.docker_running &&
    env.image_loaded &&
    env.code_extracted;

  function handleEnvCheckNext() {
    if (allReady) setPhase("env-config");
  }

  // Auto-advance when env is ready (only if user is currently on env-check)
  useEffect(() => {
    if (phase === "env-check" && initialPhaseRef.current === "env-check" && allReady && !loading) {
      const timer = setTimeout(() => setPhase("env-config"), 1500);
      return () => clearTimeout(timer);
    }
  }, [allReady, loading, phase]);

  const phaseIndex = PHASE_ORDER.indexOf(phase);
  const showDashboard = phase === "dashboard";

  return (
    <div className="app-container">
      {/* Header — hidden in dashboard mode */}
      {!showDashboard && (
        <>
          <div className="header">
            <div className="header-row">
              <div>
                <div className="header-title">🦞 CLAWBOX</div>
                <div className="header-sub">AI 自动化工具流沙盒启动器</div>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <button
                  className="theme-toggle"
                  onClick={() => window.location.reload()}
                  title="刷新页面"
                >
                  <RefreshCw size={16} />
                </button>
                <button
                  className="theme-toggle"
                  onClick={() => setTheme((t) => (t === "light" ? "dark" : "light"))}
                  title="切换主题"
                >
                  {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
                </button>
              </div>
            </div>
          </div>

          {/* Phase Steps Indicator */}
          <div className="phase-steps">
            {PHASE_ORDER.filter(p => p !== "dashboard").map((p, i) => (
              <div
                key={p}
                className={`phase-step ${i < phaseIndex ? "done" : ""} ${p === phase ? "active" : ""}`}
                onClick={() => { if (i <= phaseIndex) setPhase(p); }}
                style={{ cursor: i <= phaseIndex ? "pointer" : "default" }}
              >
                <div className="phase-step-dot">{i < phaseIndex ? "✓" : i + 1}</div>
                <span className="phase-step-label">{PHASE_LABELS[p]}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Phase Content */}
      {phase === "env-check" && (
        <PhaseEnvCheck
          env={env}
          systemInfo={systemInfo}
          loading={loading}
          status={status}
          installDir={installDir}
          setInstallDir={setInstallDir}
          onCheckEnv={checkEnv}
          addLog={addLog}
        />
      )}

      {phase === "env-config" && (
        <PhaseEnvConfig
          installDir={installDir}
          setInstallDir={setInstallDir}
          addLog={addLog}
          onSaved={() => setPhase("docker-up")}
        />
      )}

      {phase === "docker-up" && (
        <PhaseDockerUp
          installDir={installDir}
          addLog={addLog}
          onReady={(isFirstRun) => {
            if (isFirstRun) {
              setPhase("wizard");
              setWizardStep(0);
            } else {
              setPhase("dashboard");
            }
          }}
        />
      )}

      {phase === "wizard" && wizardStep === 0 && (
        <WizardStep0Admin
          addLog={addLog}
          onNext={(token) => {
            setAuthToken(token);
            setWizardStep(1);
          }}
        />
      )}

      {phase === "wizard" && wizardStep === 1 && (
        <WizardStep1Network
          token={authToken}
          addLog={addLog}
          onNext={() => setWizardStep(2)}
          onBack={() => setWizardStep(0)}
        />
      )}

      {phase === "wizard" && wizardStep === 2 && (
        <WizardStep2LLM
          token={authToken}
          addLog={addLog}
          onNext={() => setWizardStep(3)}
          onBack={() => setWizardStep(1)}
        />
      )}

      {phase === "wizard" && wizardStep === 3 && (
        <WizardStep3Finish
          token={authToken}
          addLog={addLog}
          onFinish={() => setPhase("dashboard")}
          onBack={() => setWizardStep(2)}
        />
      )}

      {phase === "dashboard" && (
        <PhaseDashboard
          installDir={installDir}
          addLog={addLog}
          onBack={() => setPhase("docker-up")}
        />
      )}

      {/* Log Output — hidden in dashboard mode */}
      {!showDashboard && (
        <div className="log-section">
          <span className="log-section-title">日志输出</span>
          <div className="log-area" ref={logRef}>
            {logs.join("\n") || "等待操作..."}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
