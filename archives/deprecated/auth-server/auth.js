import { betterAuth } from "better-auth";
import pg from "pg";

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL?.includes("sslmode=require")
    ? { rejectUnauthorized: false }
    : undefined,
});

export const auth = betterAuth({
  baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3001",
  basePath: "/auth",
  secret: process.env.BETTER_AUTH_SECRET,
  database: pool,
  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
  },
  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
    },
  },
  user: {
    additionalFields: {
      experienceLevel: {
        type: "string",
        required: false,
        defaultValue: "",
        input: true,
      },
      programmingLanguages: {
        type: "string",
        required: false,
        defaultValue: "",
        input: true,
      },
      aiMlFamiliarity: {
        type: "string",
        required: false,
        defaultValue: "",
        input: true,
      },
      hardwareExperience: {
        type: "string",
        required: false,
        defaultValue: "",
        input: true,
      },
      learningGoals: {
        type: "string",
        required: false,
        defaultValue: "",
        input: true,
      },
      questionnaireCompleted: {
        type: "boolean",
        required: false,
        defaultValue: false,
        input: true,
      },
    },
  },
  trustedOrigins: (process.env.ALLOWED_ORIGINS || "http://localhost:3000")
    .split(",")
    .map((o) => o.trim()),
});
