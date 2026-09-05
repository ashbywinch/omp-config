// Open a Loft review page with a valid session and screenshot it.
//
// `cookie` is the output of examples/make_session_cookie.py; `url` is the
// review URL (see SKILL.md for the format). With the harness browser:
//   await tab.run(code, { args: [{ cookie, url }] })
// Use page.setCookie — NEVER document.cookie: the harness `run` action
// executes in Node, not the page DOM.
async ({ page }, { cookie, url }) => {
  await page.setCookie({ name: "session", value: cookie, domain: "localhost", path: "/" });
  await page.goto(url, { waitUntil: "networkidle2" });
  await page.screenshot({ path: "review-page.png", fullPage: true });
};
