TinyContacts — Simple, test-friendly contacts web app

A minimal, clean contacts app you can build in 3–4 small projects to exercise your MCP tool’s “project → sub-agents” workflow. It’s intentionally boring (on purpose): CRUD for contacts with photo upload, phone, email, and important dates. Nothing fancy, easy to verify, and perfect for sub-agent hand-offs.

1) Product overview

Goal: Let a user add and manage contacts with:

Contact photo (upload/replace)

Name

Email

Phone number

Important dates (e.g., birthday, anniversary, custom label + date)

Keep it simple:

Single user (no auth) to reduce scope (you can bolt on auth later).

One-page UI with a modal form. Client-side validation.

Basic search/filter by name or email.

Non-goals for v1:

No multi-user accounts / auth

No social integrations, no vCard import/export (optional later)

No complicated date rules or reminders (optional later)

2) Target users & quick flow

Target user: Any individual who wants a dead-simple address book.

Happy path flow:

User opens the app → sees a list/grid of contacts (empty state with “Add Contact”).

Click Add Contact → modal form:

Upload photo (optional)

Name (required)

Email (required, validated)

Phone (optional, validated)

Important dates (0..N): each has label and date

Save → list updates instantly.

Search by name/email from a top search box.

Click a contact → detail panel (inline) with edit/delete.

Replace photo or add/edit/remove dates as needed.

3) Tech stack (pragmatic & MCP-friendly)

Frontend: React (Vite) + TypeScript + Tailwind (or minimal CSS)

UI components: Lightweight (headless) + simple HTML inputs (keep it stable for agents)

Backend: FastAPI (Python) – small, explicit, easy to test

DB: SQLite + SQLAlchemy/SQLModel (zero-config for local dev)

Storage: Local filesystem uploads/ for photos (store file path in DB)

Build/Run: uvicorn for API, vite for frontend

Testing: Pytest (API) + basic React testing (optional)

API format: JSON REST

If you need Postgres later, swap DB URL; models stay the same.

4) Data model (v1)

Contact

id: int

full_name: str (required)

email: str (required, unique)

phone: str | null

photo_url: str | null (relative path to uploads/...)

created_at: datetime

updated_at: datetime

ImportantDate

id: int

contact_id: int (FK → Contact.id)

label: str (e.g., “Birthday”, “Anniversary”, “Other”)

date: date

Validation basics

Email: simple RFC-ish check

Phone: digits, spaces, +, -, parentheses (don’t over-validate)

Photo: max size (e.g., 3MB), allow JPG/PNG, store resized copy (optional)

5) REST API (minimal)
POST   /api/contacts             # create contact (JSON, no photo)
GET    /api/contacts             # list with ?q= (search name/email)
GET    /api/contacts/{id}        # get one
PUT    /api/contacts/{id}        # update contact
DELETE /api/contacts/{id}        # delete contact

POST   /api/contacts/{id}/photo  # multipart/form-data: file
DELETE /api/contacts/{id}/photo  # remove photo

GET    /api/contacts/{id}/dates  # list important dates
POST   /api/contacts/{id}/dates  # add {label, date}
PUT    /api/dates/{date_id}      # edit
DELETE /api/dates/{date_id}      # delete


Response shape (example contact):

{
  "id": 42,
  "full_name": "Ada Lovelace",
  "email": "ada@lovelace.org",
  "phone": "+1 (555) 123-4567",
  "photo_url": "/uploads/42.jpg",
  "important_dates": [
    {"id": 7, "label": "Birthday", "date": "1815-12-10"}
  ],
  "created_at": "2025-10-23T21:30:00Z",
  "updated_at": "2025-10-23T21:30:00Z"
}

6) UI sketch (one page)

Header: “TinyContacts”, search input.

Main:

Empty state: “No contacts yet” + big Add Contact button.

Grid/List of cards: photo (or initials), name, email. Actions: View/Edit/Delete.

Modal: Add/Edit Contact

Photo uploader (drag’n’drop or button)

Name, Email, Phone

“Important dates” section: repeatable rows (Label dropdown + Date picker)

Save / Cancel

Detail slide-over (optional)

Larger photo, fields, dates, quick edit.

Keep styles neutral and readable. No design flourishes needed for the test.

7) Repo layout
tinycontacts/
  backend/
    app.py
    models.py
    schemas.py
    db.py
    routers/
      contacts.py
      dates.py
      photos.py
    uploads/                # gitignored
    tests/
      test_contacts.py
  frontend/
    index.html
    src/
      main.tsx
      App.tsx
      api.ts
      components/
        ContactList.tsx
        ContactForm.tsx
        ContactCard.tsx
        DatesEditor.tsx
    vite.config.ts
    tailwind.config.js
  .gitignore
  README.md
