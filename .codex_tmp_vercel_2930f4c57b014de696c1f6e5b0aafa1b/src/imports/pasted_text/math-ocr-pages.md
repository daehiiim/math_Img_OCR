You are editing an existing website project called **Math OCR**.

The current project already contains the main **OCR workspace page** where users upload images and convert them into HWPX files.

Do NOT redesign or modify the existing OCR workspace.
Instead, add the missing pages and flows required for authentication, ChatGPT connection, and payment.

Follow the visual style already used in the existing project.
Use a clean modern SaaS UI similar to Notion / Stripe / Vercel.

---

PROJECT DESCRIPTION

Math OCR is a tool that analyzes images of math problems and converts them into HWPX documents automatically using AI.

There are two types of users:

1. Users with a ChatGPT Plus / Pro account
   They connect their ChatGPT account and can use Math OCR for free.

2. Users without ChatGPT
   They must purchase image credits and Math OCR will use our API.

---

USER FLOW

Landing
→ Google Login
→ Choose usage type

Option A
Connect ChatGPT account
→ Go to OCR workspace

Option B
Buy image credits
→ Stripe payment
→ Return to OCR workspace

---

PAGES TO ADD

Add the following pages only.

---

PAGE 1 — LOGIN PAGE

Purpose
Allow users to sign in before using the service.

Layout

Title
Math OCR

Subtitle
Upload math images and convert them into HWPX documents instantly.

Primary button
Sign in with Google

Below the button add small helper text
Google account login required.

Style
Centered card layout with large white space.

---

PAGE 2 — USAGE SELECTION PAGE

Purpose
Let users choose how they want to use the service.

Title
Choose how you want to use Math OCR

Two large cards.

CARD 1

Title
Use with ChatGPT

Description
Connect your ChatGPT Plus or Pro account and use Math OCR for free.

Button
Connect ChatGPT

Icon suggestion
ChatGPT or AI icon

CARD 2

Title
Use without ChatGPT

Description
Purchase image credits and use Math OCR without connecting ChatGPT.

Button
Buy Credits

Icon suggestion
Credit or payment icon

Cards should be horizontally aligned.

---

PAGE 3 — CHATGPT CONNECTION PAGE

Purpose
Explain ChatGPT connection before OAuth.

Title
Connect your ChatGPT account

Description
Math OCR uses ChatGPT to analyze math expressions in images.

For the best experience, a ChatGPT Plus or Pro account is recommended.

Primary button
Connect ChatGPT

Secondary text link (grey)

Don't have ChatGPT?
Purchase image credits instead.

This link should navigate to the pricing page.

---

PAGE 4 — PRICING PAGE

Purpose
Allow users to purchase credits.

Title
Purchase Image Credits

Subtitle
Convert math images into HWPX documents instantly.

Show three pricing cards.

CARD 1

Title
Single

Price
90원

Description
1 image conversion

Button
Buy

---

CARD 2

Title
Starter

Price
5900원

Description
100 images

Price per image
59원 / image

Button
Buy

Highlight this card slightly.

---

CARD 3

Title
Pro

Price
10900원

Description
200 images

Price per image
54.5원 / image

Badge
Best Value

Button
Buy

Cards should be responsive and evenly spaced.

---

PAGE 5 — PAYMENT PAGE

Purpose
Stripe payment page.

Title
Complete your purchase

Show summary card

Example

Package
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

After successful payment

Automatically redirect to the OCR workspace.

---

GLOBAL UI COMPONENTS

Header

Left
Math OCR logo

Right
User avatar
Credits remaining indicator

Example

Credits
74 images left

---

SUCCESS FLOW

If ChatGPT connection succeeds
→ Redirect to OCR workspace

If payment succeeds
→ Add credits to user account
→ Redirect to OCR workspace

---

DESIGN STYLE

Modern SaaS dashboard style.

Clean typography
Soft shadows
Rounded cards
Minimal color palette

Primary color
Indigo or blue accent

Use consistent spacing and grid layout.

Ensure mobile responsiveness.

---

IMPORTANT

Do not modify existing OCR workspace components.
Only add the pages and flows described above.
