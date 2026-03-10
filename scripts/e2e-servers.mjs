import { spawn } from "node:child_process";
import net from "node:net";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const rootDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const serverDir = resolve(rootDir, "server");
const clientDir = resolve(rootDir, "client");

const processes = [];

function run(cmd, args, options) {
  const child = spawn(cmd, args, {
    stdio: "inherit",
    ...options,
  });
  processes.push(child);
  return child;
}

function runAndWait(cmd, args, options) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      stdio: "inherit",
      ...options,
    });
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`${cmd} exited with code ${code}`));
      }
    });
  });
}
async function waitPort(port, host = "127.0.0.1", timeoutMs = 60_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const socket = new net.Socket();
    try {
      await new Promise((resolve, reject) => {
        socket.setTimeout(1000);
        socket.once("error", reject);
        socket.once("timeout", reject);
        socket.connect(port, host, resolve);
      });
      socket.destroy();
      return;
    } catch {
      socket.destroy();
      await new Promise((r) => setTimeout(r, 500));
    }
  }
  throw new Error(`Timed out waiting for ${host}:${port}`);
}

function shutdown() {
  for (const child of processes) {
    child.kill("SIGTERM");
  }
}

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);

run("docker", ["compose", "up", "-d", "db"], { cwd: rootDir });
await waitPort(5433);

run("uv", ["run", "uvicorn", "tests.integration.agent_stub:app", "--host", "127.0.0.1", "--port", "18020"], {
  cwd: serverDir,
  env: { ...process.env },
});

await runAndWait("uv", ["run", "alembic", "upgrade", "head"], {
  cwd: serverDir,
  env: {
    ...process.env,
    DATABASE_URL: "postgresql+asyncpg://postgres:postgres@localhost:5433/app_scaffold",
  },
});

run("uv", ["run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18010"], {
  cwd: serverDir,
  env: {
    ...process.env,
    ENV: "development",
    DATABASE_URL: "postgresql+asyncpg://postgres:postgres@localhost:5433/app_scaffold",
    AGENT_SERVER_URL: "http://127.0.0.1:18020",
    AGENT_APP_NAME: "metrosearch_agent",
    JWT_SECRET: "test-secret-at-least-32-bytes-long",
    CORS_ORIGINS: "http://127.0.0.1:5173",
  },
});

run("pnpm", ["run", "dev", "--", "--port", "5173"], {
  cwd: clientDir,
  env: {
    ...process.env,
    VITE_API_BASE_URL: "http://127.0.0.1:18010",
  },
});

await waitPort(18020);
await waitPort(18010);
await waitPort(5173);

// Keep process alive for Playwright
await new Promise(() => {});
