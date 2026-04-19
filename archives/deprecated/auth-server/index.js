import "dotenv/config";
import express from "express";
import cors from "cors";
import { toNodeHandler } from "better-auth/node";
import { auth } from "./auth.js";

const PORT = process.env.AUTH_PORT || 3001;
const app = express();

// Parse allowed origins
const allowedOrigins = (process.env.ALLOWED_ORIGINS || "http://localhost:3000")
  .split(",")
  .map((o) => o.trim());

// Middleware
app.use(express.json());
app.use(
  cors({
    origin: allowedOrigins,
    credentials: true,
    methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allowedHeaders: ["Content-Type", "Authorization", "Cookie"],
  })
);

// Health check
app.get("/health", (req, res) => {
  res.json({ status: "healthy", service: "auth-server" });
});

// Better-auth handler
const betterAuthHandler = toNodeHandler(auth);

// Route all /auth/* and /api/auth/* requests to better-auth
app.use("/auth", betterAuthHandler);
app.use("/api/auth", (req, res, next) => {
  // Rewrite /api/auth/* to /auth/* for better-auth
  req.url = req.url.replace(/^\/api/, "");
  next();
}, betterAuthHandler);

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: "Not found" });
});

// Error handler
app.use((err, req, res, next) => {
  console.error("Auth server error:", err);
  res.status(500).json({ error: err.message || "Internal server error" });
});

app.listen(PORT, () => {
  console.log(`✅ Auth server running on port ${PORT}`);
  console.log(`✅ Allowed origins: ${allowedOrigins.join(", ")}`);
  console.log(`✅ OAuth endpoints ready at http://localhost:${PORT}/auth`);
});
