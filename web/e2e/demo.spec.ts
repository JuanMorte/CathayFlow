// The demo story on two screens: the slip, staff approve, the phone gets the alert, the passenger switches.
import { expect, test } from "@playwright/test";

test("demo loop: slip, approve all, alert, switch", async ({ browser }) => {
  const staff = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const phone = await browser.newPage({ viewport: { width: 390, height: 844 } });

  await staff.goto("/staff");
  await staff.getByRole("button", { name: "Start of day", exact: true }).click();
  await phone.goto("/app");
  await phone.getByText("Cathay Flow is on").click();
  await expect(phone.getByText(/connection looks good/)).toBeVisible();

  // CX254 pushes back late in London at 05:37: play a few seconds at one minute per second.
  await staff.getByRole("button", { name: "Play", exact: true }).click();
  await expect(phone.getByText(/connection is tight/)).toBeVisible({ timeout: 20_000 });
  await staff.getByRole("button", { name: "Pause", exact: true }).click();

  await staff.getByRole("button", { name: "Before landing", exact: true }).click();
  await expect(phone.getByText("Both seats are held for you")).toBeVisible();
  await expect(phone.getByText("Original · still held")).toBeVisible();
  await expect(phone.getByText("If you miss it")).toBeVisible();
  await expect(phone.getByRole("button", { name: /Switch to CX105/ })).toBeDisabled();

  await staff.getByRole("button", { name: /Approve all/ }).click();
  await expect(phone.getByText("Your options are ready")).toBeVisible();
  await phone.getByText("Tap to see your plan").click();
  await phone.getByRole("button", { name: /Switch to CX105/ }).click();
  await phone.getByRole("button", { name: "Confirm switch" }).click();
  await expect(phone.getByText(/Board CX105 in/)).toBeVisible();
  await expect(staff.getByText("✓ Rebooked on CX105")).toBeVisible({ timeout: 5_000 });
});
