import { defineConfig } from "@playwright/test";
import path from "node:path";

// ponytail: e2e-only throwaway secret and a scratch Mongo data dir — never
// used outside this local/CI test run.
const BACKEND_ENCRYPTION_KEY = "Tw2_EE2gAR7n0AZSXpJzImMTfLRJZKaemoWmS0DxmWY=";
const BACKEND_PORT = 8010;
const FRONTEND_PORT = 3010;
const BACKEND_DIR = path.join(__dirname, "..", "backend");

// Locally we spin up a throwaway mongod ourselves. In CI, a `mongo` service
// container is already running on the default port — set E2E_START_MONGO=false
// there so Playwright doesn't try (and fail) to spawn its own mongod binary.
const startMongo = process.env.E2E_START_MONGO !== "false";
const MONGO_PORT = Number(process.env.E2E_MONGO_PORT ?? 27118);
const MONGO_DATA_DIR = path.join(__dirname, "e2e", ".mongo-data");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
  },
  webServer: [
    ...(startMongo
      ? [
          {
            command: `mkdir -p ${MONGO_DATA_DIR} && mongod --dbpath ${MONGO_DATA_DIR} --port ${MONGO_PORT} --bind_ip 127.0.0.1`,
            port: MONGO_PORT,
            reuseExistingServer: false,
            timeout: 30_000,
          },
        ]
      : []),
    {
      command: `${BACKEND_DIR}/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT}`,
      cwd: BACKEND_DIR,
      port: BACKEND_PORT,
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        MONGO_URI: `mongodb://127.0.0.1:${MONGO_PORT}`,
        MONGO_DB_NAME: "dmprod_e2e",
        APP_ENCRYPTION_KEY: BACKEND_ENCRYPTION_KEY,
        JWT_SECRET: "e2e-test-secret",
        CORS_ORIGIN: `http://localhost:${FRONTEND_PORT}`,
      },
    },
    {
      command: `npm run start -- -p ${FRONTEND_PORT}`,
      port: FRONTEND_PORT,
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        API_URL: `http://127.0.0.1:${BACKEND_PORT}`,
      },
    },
  ],
});
