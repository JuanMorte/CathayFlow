// The demo story on two screens: the delay, the agent rebooks, the phone gets the alert and the new plan.
import { expect, test } from "@playwright/test";

test("demo loop: delay, agent rebooks, alert, rebooked screen", async ({ browser }) => {
  const staff = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const phone = await browser.newPage({ viewport: { width: 390, height: 844 } });

  await staff.goto("/staff");
  await staff.getByRole("button", { name: "Start of day", exact: true }).click();
  await phone.goto("/app");
  await expect(phone.getByText("Hello Ms Wijaya")).toBeVisible();
  await expect(phone.getByText(/Leave home at .* tomorrow/)).toBeVisible();

  // 13:46: CX718 is 95 minutes late; two rows wait for this agent.
  await staff.getByRole("button", { name: "Decision time", exact: true }).click();
  await expect(staff.getByText("+95 min late")).toBeVisible();
  await expect(staff.getByRole("button", { name: "Rebook", exact: true })).toHaveCount(2);
  await expect(staff.getByText(/Rebooked \d\d:\d\d/)).toHaveCount(2);
  await expect(staff.getByText("Kept on CX251")).toBeVisible();

  await phone.reload();
  await staff.getByRole("button", { name: "Rebook", exact: true }).first().click();
  await expect(phone.getByText("Your connection has changed").last()).toBeVisible();
  await phone.getByText("CATHAY", { exact: true }).click();
  await expect(phone.getByText("Your connection has been rebooked")).toBeVisible();
  await expect(phone.getByText("Flight rebooked on CX255")).toBeVisible();
  await expect(phone.getByText(/Rebooked by a Cathay agent at/)).toBeVisible();
  await expect(staff.getByText(/Rebooked \d\d:\d\d/)).toHaveCount(3, { timeout: 5_000 });
});
