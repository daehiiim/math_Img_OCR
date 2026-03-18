You are editing an existing project called **Math OCR**.

The project already contains an OCR workspace page where users upload images and convert them into HWPX documents.

Do not modify the existing OCR workspace.

Generate the missing UI screens and flows needed for authentication, credits, and payment.

Use a clean modern SaaS UI similar to Notion, Vercel, or Stripe.

---

USER FLOW

Landing
→ Google Login
→ OCR Workspace

If the user has credits
→ OCR works normally

If the user has no credits
→ Redirect to Pricing Page

After payment
→ Return to OCR Workspace

Users may optionally connect their ChatGPT account to process OCR using their own account.

---

CREATE THE FOLLOWING SCREENS

---

SCREEN 1 — LOGIN

Centered layout.

Title
Math OCR

Subtitle
Upload math images and convert them into HWPX documents automatically.

Primary button
Sign in with Google

Helper text
Google account login required to continue.

Minimal modern card layout.

---

SCREEN 2 — PRICING

Title
Purchase Image Credits

Subtitle
Convert math images into HWPX documents instantly.

Create three pricing cards.

Card 1

Title
Single

Price
90원

Description
1 image conversion

Button
Buy

---

Card 2

Title
Starter

Price
5900원

Description
100 images

Price per image
59원

Button
Buy

Highlight this card slightly.

---

Card 3

Title
Pro

Price
10900원

Description
200 images

Price per image
54.5원

Badge
Best Value

Button
Buy

Cards should be horizontally aligned.

---

SCREEN 3 — PAYMENT

Title
Complete Your Purchase

Show order summary card.

Example

Plan
Starter

Images
100

Price
5900원

Payment methods

Credit card
Apple Pay
Google Pay

Primary button
Pay Now

After successful payment redirect the user back to the OCR workspace.

---

SCREEN 4 — CHATGPT CONNECTION (OPTIONAL)

Title
Connect your ChatGPT account

Description
Math OCR can use your ChatGPT account to process math OCR.

Recommended for ChatGPT Plus or Pro users.

Primary button
Connect ChatGPT

Secondary text link
Skip and continue

This screen is optional and can be accessed from user settings.

---

GLOBAL COMPONENTS

Header

Left
Math OCR logo

Right

User avatar
Credits indicator

Example

Credits
74 images left

---

DESIGN STYLE

Modern SaaS dashboard style.

Rounded cards
Soft shadows
Clean typography
Generous white space

Primary color
Indigo or blue accent

Ensure responsive layout for desktop and tablet.

---

IMPORTANT

Do not change the existing OCR workspace.

Only add the screens described above.
