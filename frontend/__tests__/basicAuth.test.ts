import { expect, it } from "vitest";
import { basicAuthOk } from "@/lib/basicAuth";

const header = (user: string, pass: string) => `Basic ${btoa(`${user}:${pass}`)}`;

it("accepts the configured login and nothing else", () => {
  expect(basicAuthOk(header("admin", "s3cret"), "admin", "s3cret")).toBe(true);
  expect(basicAuthOk(header("admin", "wrong"), "admin", "s3cret")).toBe(false);
  expect(basicAuthOk(header("root", "s3cret"), "admin", "s3cret")).toBe(false);
  expect(basicAuthOk(null, "admin", "s3cret")).toBe(false);
  expect(basicAuthOk("Bearer xyz", "admin", "s3cret")).toBe(false);
  expect(basicAuthOk("Basic !!!not-base64", "admin", "s3cret")).toBe(false);
});

it("a password may contain a colon", () => {
  expect(basicAuthOk(header("admin", "a:b"), "admin", "a:b")).toBe(true);
});

it("without a configured login the page is open (local development)", () => {
  expect(basicAuthOk(null, undefined, undefined)).toBe(true);
});
