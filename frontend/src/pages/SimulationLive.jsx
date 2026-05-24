import { useSimulationSocket } from "../hooks/useSimulationSocket.js";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { Play, Square, Wifi, WifiOff, Zap } from "lucide-react";
import { fmtCount, fmtPct } from "../lib/utils.js";
import PageHeader from "../components/PageHeader.jsx";
import { cn } from "../lib/utils.js";
import { useRef, useEffect, useState } from "react";

const STATUS_STYLES = {
  idle:       "text-gray-500",
  connecting: "text-amber-400 animate-pulse",
  running:    "text-green-400 animate-pulse",
  complete:   "text-brand-400",
  error:      "text-red-400",
};

const STATUS_LABELS = {
  idle:       "Idle",
  connecting: "Connecting…",
  running:    "Live",
  complete:   "Complete",
  error:      "Error",
};

export default function SimulationLive() {
  const { status, stats, alerts, messages, error, connect, disconnect } =
    useSimulationSocket();

  const logRef = useRef(null);
  const [chartData, setChartData] = useState([]);

  // Build chart data from stats history
  useEffect(() => {
    if (stats) {
      setChartData((prev) => [
        ...prev.slice(-60),
        {
          t: prev.length,
          processed: stats.processed,
          alerted: stats.alerted,
          tps: stats.throughput_tps,
          alert_rate: +(stats.alert_rate * 100).toFixed(2),
        },
      ]);
    }
  }, [stats]);

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [messages]);

  const isRunning = status === "running" || status === "connecting";

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Live Simulation Stream"
        subtitle="Real-time AML rule evaluation over a streaming transaction feed via WebSocket"
      >
        <div className="flex items-center gap-2">
          <span className={cn("flex items-center gap-1.5 text-sm font-medium", STATUS_STYLES[status])}>
            {isRunning ? <Wifi size={14} /> : <WifiOff size={14} />}
            {STATUS_LABELS[status]}
          </span>
          {isRunning ? (
            <button onClick={disconnect} className="btn-ghost text-sm">
              <Square size={14} /> Stop
            </button>
          ) : (
            <button onClick={connect} className="btn-primary text-sm">
              <Play size={14} /> Start Stream
            </button>
          )}
        </div>
      </PageHeader>

      <div className="p-8 space-y-6">
        {error && (
          <div className="card border-red-500/20 bg-red-500/5 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Live KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {[
            ["Processed", fmtCount(stats?.processed), ""],
            ["Alerted", fmtCount(stats?.alerted), "text-amber-400"],
            ["Illicit Detected", fmtCount(stats?.illicit_detected), "text-red-400"],
            ["Alert Rate", fmtPct(stats?.alert_rate), ""],
            ["Throughput", stats ? `${stats.throughput_tps} tx/s` : "—", "text-green-400"],
          ].map(([label, value, color]) => (
            <div key={label} className="metric-card">
              <span className="metric-label">{label}</span>
              <span className={cn("metric-value", color)}>{value || "—"}</span>
            </div>
          ))}
        </div>

        {/* Chart + Log */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Throughput chart */}
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-4">
              Live Metrics
            </h3>
            {chartData.length > 1 ? (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="t" hide />
                  <YAxis yAxisId="left" tick={{ fill: "#6b7280", fontSize: 10 }} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fill: "#6b7280", fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ background: "#161b27", border: "1px solid #1f2937", borderRadius: 8 }}
                  />
                  <Line yAxisId="left" type="monotone" dataKey="tps" stroke="#22c55e" dot={false} name="TPS" strokeWidth={2} />
                  <Line yAxisId="right" type="monotone" dataKey="alert_rate" stroke="#f59e0b" dot={false} name="Alert %" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-32 text-gray-600 text-sm">
                {status === "idle" ? "Press Start Stream to begin" : "Waiting for data…"}
              </div>
            )}
          </div>

          {/* Event log */}
          <div className="card p-0 overflow-hidden">
            <div className="px-5 py-3 border-b border-surface-border flex items-center gap-2">
              <Zap size={13} className="text-brand-400" />
              <h3 className="text-sm font-semibold text-white">Event Log</h3>
            </div>
            <div
              ref={logRef}
              className="h-[200px] overflow-y-auto px-4 py-3 space-y-1 font-mono text-xs"
            >
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={cn(
                    msg.type === "error"   ? "text-red-400" :
                    msg.type === "success" ? "text-green-400" :
                    msg.type === "start"   ? "text-brand-400" :
                    "text-gray-400"
                  )}
                >
                  <span className="text-gray-600 mr-2">[{String(i).padStart(3, "0")}]</span>
                  {msg.text}
                </div>
              ))}
              {messages.length === 0 && (
                <p className="text-gray-600">No events yet.</p>
              )}
            </div>
          </div>
        </div>

        {/* Live alerts table */}
        <div className="card p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">
              Live Alerts  <span className="text-gray-500 font-normal">(last 500)</span>
            </h3>
            <span className="badge bg-amber-500/10 text-amber-400 border border-amber-500/20">
              {alerts.length} alerts
            </span>
          </div>
          <div className="overflow-x-auto max-h-72">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-surface-card">
                <tr className="border-b border-surface-border">
                  {["TX ID", "From Account", "Amount", "Score", "Illicit", "Typology"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {[...alerts].reverse().map((a, i) => (
                  <tr key={i} className="hover:bg-surface-hover">
                    <td className="px-4 py-2 font-mono text-gray-400">{a.tx_id}</td>
                    <td className="px-4 py-2 font-mono text-gray-300 max-w-[120px] truncate">{a.from_account}</td>
                    <td className="px-4 py-2 font-mono">${Number(a.amount || 0).toLocaleString()}</td>
                    <td className="px-4 py-2 font-mono text-brand-400 font-medium">
                      {Number(a.alert_score || 0).toFixed(2)}
                    </td>
                    <td className="px-4 py-2">
                      {a.is_illicit
                        ? <span className="badge bg-red-500/10 text-red-400">Yes</span>
                        : <span className="badge bg-green-500/10 text-green-400">No</span>}
                    </td>
                    <td className="px-4 py-2 font-mono text-gray-500">{a.illicit_typology || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {alerts.length === 0 && (
              <div className="text-center py-8 text-gray-600">
                No alerts yet — start the stream.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
