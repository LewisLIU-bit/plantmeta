import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE;
console.log("API_BASE =", API_BASE);

const statusText = {
  normal: "状态良好",
  watch: "需要关注",
  danger: "需要干预",
  fault: "设备异常",
};

const eventModeText = {
  manual: "手动浇水",
  auto: "自动浇水",
  demo: "演示浇水",
};

async function request(path, options) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
}

function formatTime(value) {
  if (!value) return "--";
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
  const normalized = hasTimezone ? value : `${value}Z`;
  return new Date(normalized).toLocaleString("zh-CN", {
    hour12: false,
    timeZone: "Asia/Shanghai",
  });
}

function Metric({ label, value, unit }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value ?? "--"}</strong>
      <small>{unit}</small>
    </div>
  );
}

function MiniChart({ data }) {
  const width = 520;
  const height = 160;
  const padding = 18;
  const values = data.map((item) => item.soil_moisture_percent);
  const dataMin = Math.min(...values, 0);
  const dataMax = Math.max(...values, 100);
  const actualMin = values.length ? Math.min(...values) : dataMin;
  const actualMax = values.length ? Math.max(...values) : dataMax;
  const range = Math.max(actualMax - actualMin, 8);
  const min = Math.max(0, actualMin - range * 0.35);
  const max = Math.min(100, actualMax + range * 0.35);

  const points = values.map((value, index) => {
    const x = padding + (index / Math.max(values.length - 1, 1)) * (width - padding * 2);
    const y = height - padding - ((value - min) / (max - min)) * (height - padding * 2);
    return `${x},${y}`;
  });

  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="土壤湿度历史曲线">
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} />
      {points.length > 1 ? <polyline points={points.join(" ")} /> : null}
      {points.map((point) => {
        const [x, y] = point.split(",");
        return <circle key={point} cx={x} cy={y} r="3" />;
      })}
    </svg>
  );
}

function App() {
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState([]);
  const [events, setEvents] = useState([]);
  const [advice, setAdvice] = useState(null);
  const [autoWatering, setAutoWatering] = useState(false);
  const [error, setError] = useState("");
  const [loadingAdvice, setLoadingAdvice] = useState(false);

  async function refresh() {
    try {
      setError("");
      const [latestData, historyData, eventData] = await Promise.all([
        request("/api/latest").catch(() => null),
        request("/api/history?limit=24"),
        request("/api/events?limit=8"),
      ]);
      setLatest(latestData);
      setHistory(historyData);
      setEvents(eventData);
    } catch (err) {
      setError(err.message);
    }
  }

  async function generateAdvice() {
    try {
      setLoadingAdvice(true);
      setError("");
      const data = await request("/api/advice", { method: "POST" });
      setAdvice(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingAdvice(false);
    }
  }

  async function manualWater() {
    try {
      setError("");
      await request("/api/water/manual", {
        method: "POST",
        body: JSON.stringify({
          duration_ms: 1000,
          reason: "前端测试面板触发手动浇水。",
        }),
      });
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function toggleAutoWatering() {
    try {
      setError("");
      const next = !autoWatering;
      const data = await request("/api/water/auto", {
        method: "POST",
        body: JSON.stringify({ enabled: next }),
      });
      setAutoWatering(data.auto_watering_enabled);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 3000);
    return () => window.clearInterval(timer);
  }, []);

  const status = latest?.status ?? "fault";

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow">PlantMeta Software Console</p>
          <h1>智能植物养护盒测试面板</h1>
          <p className="subtle">用于验证 fake ESP32、FastAPI、MySQL、规则判断和 LLM 建议链路。</p>
        </div>
        <div className={`status-badge ${status}`}>
          <span>{latest ? statusText[status] : "等待数据"}</span>
          <strong>{latest?.status ?? "no data"}</strong>
        </div>
      </section>

      {error ? <div className="error">{error}</div> : null}

      <section className="grid metrics-grid">
        <Metric label="土壤湿度" value={latest?.soil_moisture_percent} unit="%" />
        <Metric label="光照强度" value={latest?.light_lux} unit="lux" />
        <Metric label="环境温度" value={latest?.air_temperature} unit="℃" />
        <Metric label="空气湿度" value={latest?.air_humidity} unit="%" />
      </section>

      <section className="layout">
        <div className="panel wide">
          <div className="panel-head">
            <div>
              <h2>历史湿度</h2>
              <p>最近 {history.length} 条记录，数据来自 MySQL。</p>
            </div>
            <button onClick={refresh}>刷新</button>
          </div>
          <MiniChart data={history} />
        </div>

        <div className="panel">
          <h2>当前判断</h2>
          <p className="message">{latest?.message ?? "尚未收到传感器数据。"}</p>
          <p className="timestamp">最近上传：{formatTime(latest?.timestamp)}</p>
          <div className="actions">
            <button onClick={manualWater}>手动浇水测试</button>
            <button className={autoWatering ? "active" : ""} onClick={toggleAutoWatering}>
              自动模式：{autoWatering ? "开" : "关"}
            </button>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head compact">
            <h2>养护建议</h2>
            <button onClick={generateAdvice} disabled={loadingAdvice}>
              {loadingAdvice ? "生成中" : "生成建议"}
            </button>
          </div>
          <p className="message">{advice?.advice ?? "点击生成建议，测试 LLM 或模板 fallback。"}</p>
          <p className="timestamp">模型：{advice?.model_name ?? "--"}</p>
        </div>

        <div className="panel">
          <h2>浇水事件</h2>
          <div className="event-list">
            {events.length === 0 ? <p className="subtle">暂无事件。</p> : null}
            {events.map((event) => (
              <div className="event" key={event.id}>
                <strong>{eventModeText[event.mode] ?? event.mode}</strong>
                <span>{event.duration_ms} ms</span>
                <small>{formatTime(event.timestamp)}</small>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
