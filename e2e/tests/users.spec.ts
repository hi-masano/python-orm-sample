import { expect, test } from "@playwright/test";
import type { components } from "../generated/api";

type User = components["schemas"]["User"];

test("GET /users は seed ユーザーを含む", async ({ request }) => {
  const res = await request.get("/users");
  expect(res.status()).toBe(200);
  const users: User[] = await res.json();
  expect(users.map((u) => u.email)).toEqual(expect.arrayContaining(["alice@example.com", "bob@example.com"]));
});

test("POST /users → GET /users/{user_id}", async ({ request }) => {
  const email = `e2e-${Date.now()}@example.com`;
  const created = await request.post("/users", { data: { email, name: "E2E" } });
  expect(created.status()).toBe(201);
  const user: User = await created.json();
  const fetched = await request.get(`/users/${user.id}`);
  expect(fetched.status()).toBe(200);
  expect(await fetched.json()).toEqual(user);
});

test("POST /users の email 重複は 409", async ({ request }) => {
  const res = await request.post("/users", { data: { email: "alice@example.com", name: "dup" } });
  expect(res.status()).toBe(409);
});

test("存在しないユーザーは 404", async ({ request }) => {
  expect((await request.get("/users/999999")).status()).toBe(404);
});

test("limit=0 はバリデーションエラー 422", async ({ request }) => {
  expect((await request.get("/users?limit=0")).status()).toBe(422);
});
