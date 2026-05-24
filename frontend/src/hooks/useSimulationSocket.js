import { useCallback, useEffect, useRef, useState } from "react";

const WS_URL = "ws://localhost:8000/ws/simulate";

export function useSimulationSocket() {
  const [status, setStatus] = useState("idle"); // idle | connecting | running | complete | error
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);

  const addMessage = useCallback((msg) => {
    setMessages((prev) => [...prev.slice(-99), msg]);
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("connecting");
    setAlerts([]);
    setMessages([]);
    setError(null);
    setStats(null);

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("running");
      addMessage({ type: "info", text: "Connected to simulation server" });
    };

    ws.onmessage = (ev) => {
      try {
        const event = JSON.parse(ev.data);
        switch (event.type) {
          case "start":
            addMessage({ type: "start", text: event.message });
            break;
          case "progress":
            if (event.stats) setStats(event.stats);
            if (event.new_alerts?.length) {
              setAlerts((prev) => [...prev, ...event.new_alerts].slice(-500));
            }
            if (event.message) addMessage({ type: "info", text: event.message });
            break;
          case "complete":
            setStatus("complete");
            if (event.stats) setStats(event.stats);
            addMessage({ type: "success", text: "Simulation stream complete!" });
            break;
          case "error":
            setStatus("error");
            setError(event.message);
            addMessage({ type: "error", text: event.message });
            break;
          default:
            break;
        }
      } catch (e) {
        console.error("WS parse error", e);
      }
    };

    ws.onerror = () => {
      setStatus("error");
      setError("WebSocket connection failed. Is the API running on port 8000?");
    };

    ws.onclose = () => {
      if (status !== "complete") setStatus("idle");
    };
  }, [addMessage, status]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    setStatus("idle");
  }, []);

  useEffect(() => () => wsRef.current?.close(), []);

  return { status, stats, alerts, messages, error, connect, disconnect };
}
