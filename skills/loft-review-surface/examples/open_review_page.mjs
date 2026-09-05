// Open a Loft review page with a valid session and screenshot it.
//
// `cookie` is the output of examples/make_session_cookie.py; `url` is the
// review URL (see SKILL.md for the format). With the harness browser:
//   await tab.run(code, { args: [{ cookie, url }] })
// Use page.setCookie — NEVER document.cookie: the harness `run` action
// executes in Node, not the page DOM. The cookie domain is derived from the
// URL's hostname so the session applies whatever host the page is opened on
// (localhost, 127.0.0.1, or a LAN address).
async ({ page }, { cookie, url }) => {
  const { hostname } = new URL(url);
  await page.setCookie({ name: "session", value: cookie, domain: hostname, path: "/" });
  await page.goto(url, { waitUntil: "networkidle2" });
  await page.screenshot({ path: "review-page.png", fullPage: true });
};
