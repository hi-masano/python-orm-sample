import { expect, test } from "@playwright/test";
import type { components } from "../generated/api";

type Post = components["schemas"]["Post"];
type User = components["schemas"]["User"];

async function alice(request: import("@playwright/test").APIRequestContext): Promise<User> {
  const users: User[] = await (await request.get("/users?limit=100")).json();
  return users.find((u) => u.email === "alice@example.com")!;
}

test("GET /posts?tag=orm は seed の投稿を返す", async ({ request }) => {
  const posts: Post[] = await (await request.get("/posts?tag=orm")).json();
  expect(posts.map((p) => p.title)).toContain("SQLAlchemy入門");
  for (const p of posts) expect(p.tags.map((t) => t.name)).toContain("orm");
});

test("POST /posts → GET → DELETE → 404", async ({ request }) => {
  const author = await alice(request);
  const tag = `e2e-${Date.now()}`;
  const created = await request.post("/posts", {
    data: { author_id: author.id, title: "E2E 投稿", body: "本文", tag_names: [tag, tag] },
  });
  expect(created.status()).toBe(201);
  const post: Post = await created.json();
  expect(post.published).toBe(false);
  expect(post.tags.map((t) => t.name)).toEqual([tag]);

  expect((await request.get(`/posts/${post.id}`)).status()).toBe(200);
  expect((await request.delete(`/posts/${post.id}`)).status()).toBe(204);
  expect((await request.get(`/posts/${post.id}`)).status()).toBe(404);
});

test("存在しない author は 400", async ({ request }) => {
  const res = await request.post("/posts", { data: { author_id: 999999, title: "x", body: "y" } });
  expect(res.status()).toBe(400);
});

test("GET /tags は seed タグを含む", async ({ request }) => {
  const tags = await (await request.get("/tags")).json();
  expect(tags.map((t: { name: string }) => t.name)).toEqual(expect.arrayContaining(["fastapi", "orm", "python"]));
});
