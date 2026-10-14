import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { errorMessage } from "../api/client";

// Sign up page for users -- Register as a pitcher

export default function Register() {
    const { register } = useAuth();
    const navigate = useNavigate();
    const [form, setForm] = useState({ username: "", email: "", password: "" });
    const [error, setError] = useState("");
    const [submitting, setSubmitting] = useState(false);

    const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register(form.username, form.email, form.password);
      navigate("/check-in");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} style={{ display: "grid", gap: 12, maxWidth: 320, margin: "0 auto" }}>
      <h2>Create account</h2>
      <input name="username" placeholder="Username" value={form.username} onChange={onChange} required />
      <input name="email" type="email" placeholder="Email" value={form.email} onChange={onChange} required />
      <input name="password" type="password" placeholder="Password" value={form.password} onChange={onChange} required />
      <button type="submit" disabled={submitting}>{submitting ? "Creating..." : "Sign up"}</button>
      {error && <p style={{ color: "#d33", whiteSpace: "pre-line" }}>{error}</p>}
      <p>Already have an account? <Link to="/login">Log in</Link></p>
    </form>
  );
}