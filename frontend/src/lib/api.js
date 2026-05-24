const API_BASE = import.meta.env.VITE_API_BASE || "";

async function request(path) {
  const res = await fetch(`${API_BASE}/api${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export const api = {
  health:               ()          => request("/health"),
  summary:              ()          => request("/summary"),
  universes:            ()          => request("/universes"),
  universe:             (id)        => request(`/universes/${id}`),
  alerts:               (id, limit) => request(`/universes/${id}/alerts?limit=${limit ?? 200}`),
  autopsy:              (id)        => request(`/universes/${id}/autopsy`),
  recommendations:      ()          => request("/recommendations"),
  metricsComparison:    ()          => request("/metrics/comparison"),
  graph:                (limit)     => request(`/graph?limit=${limit ?? 400}`),
  mutations:            ()          => request("/mutations"),
  backtesting:          ()          => request("/backtesting"),
  backtestingUniverse:  (id)        => request(`/backtesting/${id}`),
  sar:                  ()          => request("/sar"),
  sarReport:            (id)        => request(`/sar/${id}`),
  shap:                 (id)        => request(`/shap/${id}`),
  cases:                (id)        => request(`/cases/${id}`),
  drift:                ()          => request("/drift"),
  chat:                 (msg)       => fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: msg }),
  }).then(r => r.json()),
  chatReset:            ()          => fetch(`${API_BASE}/api/chat/reset`, { method: "POST" }),
};
