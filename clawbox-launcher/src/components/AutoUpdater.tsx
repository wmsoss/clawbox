import { useEffect, useState } from "react";
import { check } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { Download, X, RefreshCw } from "lucide-react";

export default function AutoUpdater() {
  const [updateInfo, setUpdateInfo] = useState<{
    version: string;
    body: string;
  } | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [status, setStatus] = useState<string>("");
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // Delay check to avoid blocking startup
    const timer = setTimeout(() => {
      checkForUpdate();
    }, 3000);
    return () => clearTimeout(timer);
  }, []);

  async function checkForUpdate() {
    try {
      const update = await check();
      if (update) {
        setUpdateInfo({
          version: update.version,
          body: update.body ?? "",
        });
      }
    } catch (e) {
      console.log("Update check failed:", e);
    }
  }

  async function performUpdate() {
    try {
      setStatus("正在下载更新...");
      setProgress(0);

      const update = await check();
      if (!update) return;

      let totalLen = 0;
      let downloaded = 0;

      await update.downloadAndInstall((event) => {
        switch (event.event) {
          case "Started":
            totalLen = (event.data as { contentLength?: number }).contentLength ?? 0;
            break;
          case "Progress": {
            const len = (event.data as { chunkLength: number }).chunkLength;
            downloaded += len;
            if (totalLen > 0) {
              setProgress(Math.round((downloaded / totalLen) * 100));
            }
            break;
          }
          case "Finished":
            setStatus("下载完成，正在安装...");
            setProgress(100);
            break;
        }
      });

      setStatus("安装完成，即将重启...");
      await new Promise((r) => setTimeout(r, 1000));
      await relaunch();
    } catch (e) {
      setStatus(`更新失败: ${e}`);
      setProgress(null);
    }
  }

  if (!updateInfo || dismissed) return null;

  return (
    <div className="update-banner">
      <div className="update-banner-content">
        <div className="update-banner-info">
          <RefreshCw size={14} className="update-icon" />
          <span>
            发现新版本 <strong>v{updateInfo.version}</strong>
          </span>
        </div>

        {progress === null ? (
          <div className="update-banner-actions">
            <button className="neu-btn neu-btn-sm update-btn-primary" onClick={performUpdate}>
              <Download size={12} /> 立即更新
            </button>
            <button
              className="neu-btn neu-btn-sm"
              onClick={() => setDismissed(true)}
              title="稍后再说"
            >
              <X size={12} />
            </button>
          </div>
        ) : (
          <div className="update-progress-wrap">
            <span className="update-status">{status}</span>
            <div className="update-progress-bar">
              <div
                className="update-progress-fill"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
