import { useState } from "react";
import { ArrowLeft, Loader2, Rocket, CheckCircle2 } from "lucide-react";

interface Props {
  token: string;
  addLog: (msg: string) => void;
  onFinish: () => void;
  onBack: () => void;
}

export default function WizardStep3Finish({ token, addLog, onFinish, onBack }: Props) {
  const [starting, setStarting] = useState(false);
  const [done, setDone] = useState(false);

  async function handleFinish() {
    setStarting(true);
    addLog("启动引擎...");

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/agent/start", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "启动失败");
      }

      addLog("引擎启动成功！");
      setDone(true);
      setTimeout(onFinish, 1000);
    } catch (err: any) {
      addLog(`启动失败: ${err.message}`);
      setStarting(false);
    }
  }

  return (
    <div className="wizard-step" style={{ textAlign: "center" }}>
      {done ? (
        <>
          <CheckCircle2 size={48} color="var(--green)" style={{ marginBottom: 16 }} />
          <div className="wizard-step-title">🎉 配置完成</div>
          <p className="wizard-step-desc">正在进入控制台...</p>
        </>
      ) : (
        <>
          <div className="wizard-step-title">✅ 配置就绪</div>
          <p className="wizard-step-desc">
            所有基本配置已完成。点击下方按钮启动引擎并进入控制台。
          </p>

          <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
            <button
              className="neu-btn neu-btn-primary"
              style={{ height: 48, fontSize: 15, padding: "0 40px" }}
              onClick={handleFinish}
              disabled={starting}
            >
              {starting ? <Loader2 size={18} className="spin" /> : <Rocket size={18} />}
              {starting ? " 启动中..." : " 启动引擎，进入控制台"}
            </button>

            <button className="neu-btn" onClick={onBack} disabled={starting} style={{ height: 36 }}>
              <ArrowLeft size={14} /> 返回修改
            </button>
          </div>
        </>
      )}
    </div>
  );
}
