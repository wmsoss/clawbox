import { useState, useEffect, useRef } from "react";
import { ArrowLeft, ExternalLink, RefreshCw, Square, RotateCcw } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import type { ActionResult } from "../types";

interface Props {
  installDir: string;
  addLog: (msg: string) => void;
  onBack: () => void;
}

export default function PhaseDashboard({ installDir, addLog, onBack }: Props) {
  const [iframeKey, setIframeKey] = useState(0);
  const [operating, setOperating] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Override window.open at parent level — Tauri WebView's window.open
  // doesn't work, so we route it through open_url
  useEffect(() => {
    const origOpen = window.open;
    window.open = function (url?: string | URL, _target?: string, _features?: string) {
      if (url) {
        invoke("open_url", { url: String(url) });
        return null;
      }
      return origOpen.call(window, url, _target, _features);
    } as typeof window.open;

    // Also listen for clicks on the main document that might bubble from iframe
    const handleClick = (e: MouseEvent) => {
      const anchor = (e.target as HTMLElement)?.closest?.("a");
      if (anchor && anchor.target === "_blank" && anchor.href) {
        e.preventDefault();
        invoke("open_url", { url: anchor.href });
      }
    };
    document.addEventListener("click", handleClick, true);

    return () => {
      window.open = origOpen;
      document.removeEventListener("click", handleClick, true);
    };
  }, []);

  function openInBrowser() {
    invoke("open_url", { url: "http://127.0.0.1:8000" });
  }

  async function handleCompose(action: string, label: string) {
    if (operating) return;
    if (!window.confirm(`确认${label} Clawbox 容器？`)) return;
    setOperating(true);
    addLog(`${label}中...`);
    try {
      const command = action === "stop" ? "compose_down"
                    : action === "restart" ? "compose_restart"
                    : "compose_up";
      const result = await invoke<ActionResult>(command, {
        composeFile: "docker-compose.yml",
        workDir: installDir,
      });
      addLog(result.message || `${label}完成`);
      if (action !== "stop") {
        setTimeout(() => setIframeKey(k => k + 1), 2000);
      }
    } catch (e) {
      addLog(`${label}失败: ${e}`);
    } finally {
      setOperating(false);
    }
  }

  return (
    <div className="phase-dashboard">
      <div className="dashboard-toolbar">
        <button className="neu-btn neu-btn-sm" onClick={onBack} title="返回启动器">
          <ArrowLeft size={13} /> 启动器
        </button>
        <span style={{ fontSize: 12, color: "var(--text3)" }}>ClawBox 控制台</span>
        <div style={{ display: "flex", gap: 4 }}>
          <button
            className="neu-btn neu-btn-sm"
            onClick={() => handleCompose("restart", "重启")}
            disabled={operating}
            title="重启容器"
          >
            <RotateCcw size={12} />
          </button>
          <button
            className="neu-btn neu-btn-sm"
            onClick={() => handleCompose("stop", "停止")}
            disabled={operating}
            title="停止容器"
            style={{ color: "var(--red, #e53935)" }}
          >
            <Square size={12} />
          </button>
          <button className="neu-btn neu-btn-sm" onClick={() => setIframeKey(k => k + 1)} title="刷新">
            <RefreshCw size={12} />
          </button>
          <button className="neu-btn neu-btn-sm" onClick={openInBrowser} title="在浏览器中打开">
            <ExternalLink size={12} />
          </button>
        </div>
      </div>
      <iframe
        ref={iframeRef}
        key={iframeKey}
        src="http://127.0.0.1:8000/"
        className="dashboard-iframe"
        title="ClawBox Dashboard"
      />
    </div>
  );
}
