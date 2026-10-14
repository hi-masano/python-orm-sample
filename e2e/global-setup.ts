import { execSync } from "node:child_process";
import path from "node:path";

export default async function globalSetup(): Promise<void> {
  const root = path.resolve(__dirname, "..");
  execSync("docker compose exec -T api python -m seeds.run --profile e2e", { cwd: root, stdio: "inherit" });
}
