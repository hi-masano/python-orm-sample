import { expect, test } from "@playwright/test";

test("GET /health は ok", async ({ request }) => {
  const res = await request.get("/health");
  expect(res.status()).toBe(200);
  expect(await res.json()).toEqual({ status: "ok" });
});

test("GET /openapi.json は仕様ファイルを返す", async ({ request }) => {
  const spec = await (await request.get("/openapi.json")).json();
  expect(spec.info.title).toBe("python-orm-sample API");
});
