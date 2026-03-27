import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { HelpCircle, X, FolderOpen, FolderSearch, Save } from "lucide-react";
import type { ActionResult, EnvData } from "../types";

interface Props {
  installDir: string;
  setInstallDir: (dir: string) => void;
  addLog: (msg: string) => void;
  onSaved: () => void;
}

const envFields = [
  {
    key: "GITHUB_TOKEN",
    label: "GitHub Token",
    required: false,
    placeholder: "ghp_xxxx（用于通过代理拉取 GitHub 仓库）",
    help: "GitHub Personal Access Token，用于技能安装时通过代理拉取 GitHub 仓库。\n\n📋 获取步骤：\n1. 打开 https://github.com/settings/tokens\n2. 点击 'Generate new token (classic)'\n3. 勾选 'repo' 权限\n4. 点击生成，复制 token\n\n⚠ 如果不安装 GitHub 技能可留空。",
  },
  {
    key: "CLAWHUB_TOKEN",
    label: "ClawHub Token",
    required: false,
    placeholder: "clh_xxxx（OpenClaw Agent 认证）",
    help: "ClawHub Token，用于 OpenClaw Agent 认证。\n\n📋 获取步骤：\n1. 打开 https://clawhub.com\n2. 进入 Settings → API Tokens\n3. 创建新 Token 并复制\n\n⚠ 如果不使用 ClawHub 可留空。",
  },
];

export default function PhaseEnvConfig({ installDir, setInstallDir, addLog, onSaved }: Props) {
  const [envData, setEnvData] = useState<EnvData>({});
  const [helpKey, setHelpKey] = useState<string | null>(null);

  useEffect(() => {
    loadEnv();
  }, []);

  async function loadEnv() {
    try {
      const envPath = `${installDir}/.env`;
      const result = await invoke<{ success: boolean; message: string; data: EnvData | null }>(
        "read_env",
        { path: envPath }
      );
      if (result.success && result.data) {
        setEnvData(result.data);
        addLog(result.message);
      }
    } catch (e) {
      addLog(`读取 .env: ${e}`);
    }
  }

  async function saveEnv() {
    try {
      // Auto-generate JWT if missing
      let data = { ...envData };
      if (!data.JWT_SECRET_KEY) {
        const secret = await invoke<string>("generate_jwt_secret");
        data.JWT_SECRET_KEY = secret;
        addLog(`JWT_SECRET_KEY 已自动生成`);
      }
      const envPath = `${installDir}/.env`;
      const templatePath = `${installDir}/.env.example`;
      const result = await invoke<ActionResult>("write_env", {
        path: envPath,
        data: data,
        templatePath: templatePath,
      });
      addLog(result.message);
      if (result.success) {
        onSaved();
      }
    } catch (e) {
      addLog(`保存 .env 失败: ${e}`);
    }
  }

  async function pickInstallDir() {
    try {
      const selected = await invoke<string | null>("pick_directory");
      if (selected) {
        setInstallDir(selected);
        addLog(`安装目录设为: ${selected}`);
      }
    } catch (e) {
      addLog(`选择目录失败: ${e}`);
    }
  }

  return (
    <div className="phase-content">
      <div className="phase-title">⚙️ 环境配置</div>
      <p className="phase-desc">配置运行所需的环境变量。JWT 密钥将自动生成，无需手动填写。</p>

      {/* Install Directory */}
      <div className="neu-card" style={{ padding: "12px 16px", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <FolderSearch size={14} />
          <span style={{ fontSize: 13, fontWeight: 600, whiteSpace: "nowrap" }}>安装目录</span>
          <input
            className="neu-input"
            style={{ flex: 1, padding: "6px 10px", fontSize: 12 }}
            value={installDir}
            onChange={(e) => setInstallDir(e.target.value)}
          />
          <button className="neu-btn neu-btn-sm" onClick={pickInstallDir}>
            <FolderOpen size={12} /> 选择
          </button>
        </div>
      </div>

      {/* Env Fields */}
      <div className="neu-card" style={{ padding: "12px 16px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {envFields.map((field) => (
            <div key={field.key}>
              <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 4 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text2)" }}>
                  {field.label}
                </span>
                <span style={{ fontSize: 10, color: "var(--text3)" }}>选填</span>
                <button
                  style={{
                    background: "none", border: "none", cursor: "pointer",
                    color: "var(--text3)", padding: 0, display: "flex",
                  }}
                  onClick={() => setHelpKey(helpKey === field.key ? null : field.key)}
                  title="查看说明"
                >
                  <HelpCircle size={13} />
                </button>
              </div>
              {helpKey === field.key && (
                <div className="neu-card-inset" style={{
                  fontSize: 11, lineHeight: 1.6, color: "var(--text2)",
                  padding: "8px 12px", marginBottom: 6, whiteSpace: "pre-line",
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                    <div>{field.help}</div>
                    <button
                      style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text3)", padding: 0, flexShrink: 0 }}
                      onClick={() => setHelpKey(null)}
                    >
                      <X size={12} />
                    </button>
                  </div>
                </div>
              )}
              <input
                className="neu-input"
                value={envData[field.key] || ""}
                onChange={(e) => setEnvData((prev) => ({ ...prev, [field.key]: e.target.value }))}
                placeholder={field.placeholder}
                style={{ width: "100%" }}
              />
            </div>
          ))}

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
            <button className="neu-btn neu-btn-sm" onClick={loadEnv}>
              <FolderOpen size={12} /> 重新读取
            </button>
            <button className="neu-btn neu-btn-sm neu-btn-primary" onClick={saveEnv}>
              <Save size={12} /> 保存并继续
            </button>
          </div>

          <div style={{ fontSize: 11, color: "var(--text3)", textAlign: "center" }}>
            💡 以上配置全部选填。不填也可以正常使用基础功能。
          </div>
        </div>
      </div>
    </div>
  );
}
