import axios from "axios";

const api = axios.create({baseURL: "/api"});

// Add the access token to certain requests

api.interceptors.request.use((config) => {
    const requestPath = config.url?.split("?")[0];
    const isPublicAuthRequest = ["/auth/register/", "/auth/login/", "/auth/refresh/"]
        .includes(requestPath);
    const token = isPublicAuthRequest ? null : localStorage.getItem("access");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

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