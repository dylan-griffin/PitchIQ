import {createContext, useContext, useEffect, useState} from "react";
import api from "../api/client";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

function clearAuthTokens(){
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
}

export function AuthProvider({children}) {
    // State to hold the current user and loading status
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // Check if the user is already logged in
    useEffect(() => {
        if (!localStorage.getItem("access")){
            setLoading(false);
            return;
        }

        api.get("/auth/me/")
            .then((response) => setUser(response.data))
            .catch((error) => {
                setUser(null);
                if (error.response?.status === 401) {
                    clearAuthTokens();
                }
            })
            .finally(() => setLoading(false));
    }, []);

    // When client.js can't refresh the token
    useEffect(() => {
        const onForcedLogout = () => setUser(null);
        window.addEventListener("auth:logout", onForcedLogout);
        return () => window.removeEventListener("auth:logout", onForcedLogout);
    }, []);

    // Function to log in a user
    const login = async (username, password) => {
        const { data } = await api.post("/auth/login/", { username, password });
        localStorage.setItem("access", data.access);
        localStorage.setItem("refresh", data.refresh);
        
        try {
            const me = await api.get("/auth/me/");
            setUser(me.data);
            return me.data;
        } catch (error) {
            clearAuthTokens();
            setUser(null);
            throw error;
        }
    };

    // Function to register a new user and log them in
    const register = async (username, email, password) => {
        await api.post("/auth/register/", { username, email, password });
        return login(username, password);
    };

    // Function to log out the user
    const logout = () => {
        clearAuthTokens();
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
}