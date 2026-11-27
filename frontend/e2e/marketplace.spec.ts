import { expect, test } from "@playwright/test";

test.describe("MaanCamera Live Marketplace E2E", () => {
  test("search page displays zero mock data when no studios match filters", async ({ page }) => {
    const dialogs: string[] = [];
    page.on("dialog", (dialog) => {
      dialogs.push(dialog.message());
      dialog.dismiss();
    });

    await page.goto("/search?city=Jaipur");
    await expect(page.getByRole("heading", { name: "Find Creative Professionals" })).toBeVisible();
    await expect(page.getByText("No matching professionals found")).toBeVisible();
    await expect(page.getByText("Varanasi Heritage Lens")).toHaveCount(0);
    expect(dialogs).toHaveLength(0);
  });

  test("full end-to-end journey: customer enquiry -> pro quotation -> accept -> mock capture -> review -> admin approval", async ({
    page,
  }) => {
    const dialogs: string[] = [];
    page.on("dialog", (dialog) => {
      dialogs.push(dialog.message());
      dialog.dismiss();
    });

    const uniqueTitle = `E2E Candid Shoot ${Date.now()}`;
    const uniqueReview = `Seamless E2E photography delivery ${Date.now()}`;

    // 1. Customer signs in & discovers real studio on /search -> opens profile -> submits enquiry
    await page.goto("/login");
    await page.getByPlaceholder("name@example.com").fill("arjun.mehta@example.com");
    await page.getByPlaceholder("••••••••").fill("DevPass@2026!");
    await page.getByRole("button", { name: "Sign In to Account" }).click();
    await expect(page).toHaveURL(/\/customer\/dashboard/);

    await page.goto("/search?city=Pune");
    await expect(page.getByRole("link", { name: "Aura Weddings" }).first()).toBeVisible();
    await page.getByRole("link", { name: "View Portfolio" }).first().click();
    await expect(page).toHaveURL(/\/professionals\//);

    await page.getByRole("button", { name: "Request Quotation" }).click();
    await page.getByPlaceholder("e.g. 2-Day Wedding Candid & Highlight Film").fill(uniqueTitle);
    await page.getByPlaceholder("e.g. Koregaon Park").fill("Baner, Pune");
    await page
      .getByPlaceholder("Share shoot timings, deliverables needed, and style preferences...")
      .fill("Full day wedding photography + color graded deliverables.");
    await page.getByRole("button", { name: "Submit Enquiry" }).click();
    await expect(page).toHaveURL(/\/customer\/dashboard/);

    await page.getByRole("button", { name: "Sign Out" }).click();

    // 2. Professional signs in & sends digital quotation
    await page.goto("/login");
    await page.getByPlaceholder("name@example.com").fill("contact@auraweddings.com");
    await page.getByPlaceholder("••••••••").fill("DevPass@2026!");
    await page.getByRole("button", { name: "Sign In to Account" }).click();
    await expect(page).toHaveURL(/\/professional\/dashboard/);

    const leadCard = page
      .locator("div", { hasText: uniqueTitle })
      .filter({ has: page.getByRole("button", { name: "Send Quotation" }) })
      .first();
    await expect(leadCard).toBeVisible();
    await leadCard.getByRole("button", { name: "Send Quotation" }).click();
    await page.locator("form textarea").fill("Candid team + 400 retouched images.");
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByText("Digital quotation sent to customer.")).toBeVisible();

    await page.getByRole("button", { name: "Sign Out" }).click();

    // 3. Customer accepts quotation, completes mock advance payment, marks shoot completed, and submits review
    await page.goto("/login");
    await page.getByPlaceholder("name@example.com").fill("arjun.mehta@example.com");
    await page.getByPlaceholder("••••••••").fill("DevPass@2026!");
    await page.getByRole("button", { name: "Sign In to Account" }).click();
    await expect(page).toHaveURL(/\/customer\/dashboard/);

    await page.getByRole("button", { name: /My Enquiries/ }).click();
    const enqCard = page
      .locator("div", { hasText: uniqueTitle })
      .filter({ has: page.getByRole("button", { name: "Review Quotations" }) })
      .first();
    await enqCard.getByRole("button", { name: "Review Quotations" }).click();
    await page.getByRole("button", { name: "Accept Quotation & Create Booking" }).click();
    await expect(page.getByText("Quotation accepted and booking created.")).toBeVisible();

    const bookingCard = page
      .locator("div", { hasText: "Baner, Pune" })
      .filter({ has: page.getByRole("button", { name: /Pay \/ Ledger/ }) })
      .first();
    await bookingCard.getByRole("button", { name: /Pay \/ Ledger/ }).click();
    await page.getByRole("button", { name: "Create Payment Order" }).click();
    await page.getByRole("button", { name: "Complete Dev Mock Payment" }).click();
    await expect(page.getByText("Dev mock payment captured cleanly!")).toBeVisible();
    await page.getByRole("button", { name: "Close" }).click();

    await bookingCard.getByRole("button", { name: "Mark Completed" }).click();
    await bookingCard.getByRole("button", { name: "Submit Verified Review" }).click();
    await page
      .getByPlaceholder("Share your honest experience about delivery quality, punctuality, and communication...")
      .fill(uniqueReview);
    await page.getByRole("button", { name: "Submit Review" }).click();
    await expect(page.getByText("Review submitted!")).toBeVisible();

    await page.getByRole("button", { name: "Sign Out" }).click();

    // 4. Admin approves review cleanly in live moderation queue
    await page.goto("/login");
    await page.getByPlaceholder("name@example.com").fill("admin@maancamera.com");
    await page.getByPlaceholder("••••••••").fill("DevAdmin@2026!");
    await page.getByRole("button", { name: "Sign In to Account" }).click();
    await expect(page).toHaveURL(/\/admin\/dashboard/);

    const reviewCard = page
      .locator("div", { hasText: uniqueReview })
      .filter({ has: page.getByRole("button", { name: "Approve" }) })
      .first();
    await expect(reviewCard).toBeVisible();
    await reviewCard.getByRole("button", { name: "Approve" }).click();
    await expect(page.getByText("Review status updated to 'approved'.")).toBeVisible();

    expect(dialogs).toHaveLength(0);
  });
});
