import axios from "axios";

const api = axios.create({baseURL: "/api"});

const AUTH_PATHS = ["/auth/login/", "/auth/register/", "/auth/refresh/", "/health/"];
const isAuthPath = (url = "") => AUTH_PATHS.some((p) => url.includes(p));

// Add the access token to certain requests

api.interceptors.request.use((config) => {
    const requestPath = config.url?.split("?")[0];
    const token = isAuthPath(requestPath) ? null : localStorage.getItem("access");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

// One shared refresh call, so parallel 401s don't each hit /auth/refresh/
let refreshPromise = null;

function refreshAccessToken() {
    const refresh = localStorage.getItem("refresh");
    if (!refresh) return Promise.reject(new Error("No refresh token"));

    // If a refresh is already in progress, reuse the existing promise
    if (!refreshPromise) {
        refreshPromise = axios
            .post("/api/auth/refresh/", { refresh })
            .then(({ data }) => {
                localStorage.setItem("access", data.access);
                if (data.refresh) localStorage.setItem("refresh", data.refresh);
                return data.access;
            })
            // Clear state so future token expirations can trigger a new call
            .finally(() => {
                refreshPromise = null;
            })
    }
    return refreshPromise;
}

api.interceptors.response.use(
    (res) => res, // Successful responses can pass straight through
    async (error) => {
        const original = error.config;
        const status = error.response?.status;

        // Catching 401 Unauthorized errors
        if (status === 401 && original && !original._retried && !isAuthPath(original.url)) {
            original._retried = true;
            try {
                // Attempt token refresh
                const newAccess = await refreshAccessToken();
                original.headers.Authorization = `Bearer ${newAccess}`;
                return api(original);
            } catch {
                // If refresh fails signal a logout
                localStorage.removeItem("access");
                localStorage.removeItem("refresh");
                window.dispatchEvent(new Event("auth:logout"));
            }
        }
        return Promise.reject(error);
    }
);

export default api;

// For handling errors

export function errorMessage(err){
    const data = err.response?.data;
    if (!data) return "Cannot reach the server.";
    if (typeof data === "string") {
        return data.trimStart().startsWith("<")
            ? `Unexpected server response (HTTP ${err.response.status}).`
            : data;
    }
    if (typeof data.detail === "string") return data.detail;
    return Object.entries(data)
        .map(([field, messages]) => `${field}: ${[].concat(messages).join(" ")}`)
        .join("\n");
}