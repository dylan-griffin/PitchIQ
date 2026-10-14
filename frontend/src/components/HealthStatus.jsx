import { useEffect, useState } from 'react';
import api from '../api/client';

// Displays an indicator for the health status of the API
// Ensures that backend and frontend are running and communicating properly

export default function HealthStatus() {
    const [status, setStatus] = useState("checking");

    useEffect(() => {
        api.get("/health/")
            .then((response) => setStatus(response.data.status === "ok" ? "up" : "down"))
            .catch(() => setStatus("down"))
    }, []);

    const label = { checking: "Checking API...", up: "API online", down: "API unreachable" }[status];
    const color = { checking: "#999", up: "#2e9e4f", down: "#d33" }[status];

    return <p style={{ color, fontSize: 14 }}>{label}</p>;
}