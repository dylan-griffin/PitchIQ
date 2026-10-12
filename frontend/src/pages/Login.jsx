import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { errorMessage } from "../api/client";

// Login page for users -- Used to login as a pitcher (managers/coaches are assigned by admins)

export default function Login() {
    const { login } = useAuth();
    const navigate = useNavigate();
    const [form, setForm] = useState({ username: "", password: "" });
    const [error, setError] = useState("");
    const [submitting, setSubmitting] = useState(false);

    const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });
    
    const onSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setSubmitting(true);
        try {
            const user = await login(form.username, form.password);
            navigate(user.role === "pitcher" ? "/check-in" : "/dashboard");
        } catch (err) {
            setError(err.response?.status === 401 ? "Invalid username or password" : errorMessage(err));
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <form onSubmit={onSubmit} style={{ display: "grid", gap: 12, maxWidth: 320, margin: "0 auto" }}>
        <h2>Log in</h2>
        <input name="username" placeholder="Username" value={form.username} onChange={onChange} required />
        <input name="password" type="password" placeholder="Password" value={form.password} onChange={onChange} required />
        <button type="submit" disabled={submitting}>{submitting ? "Logging in..." : "Log in"}</button>
        {error && <p style={{ color: "#d33", whiteSpace: "pre-line" }}>{error}</p>}
        <p>No account? <Link to="/register">Sign up</Link></p>
        </form>
    );
}