# SwapShelf Assignment

**Student:** Beren Dogar  
**Hosted URL:** https://swapshelf-beren-dogar.onrender.com  
**Repository:** https://github.com/Berendogar/SwapShelf

## Architecture

```text
Browser -> urls.py -> views.py -> forms.py / models.py -> SQLite (data/swapshelf.db)
                         |
                         -> templates/market/*.html
```

Server-rendered Django app. Django auth handles accounts and sessions. The `market`
app has listings, message threads and messages.

## How a listing id becomes a row

`/listings/3/` matches `listings/<int:pk>/` and calls `listing_detail(pk=3)`.
`get_object_or_404(Listing, pk=3)` loads row 3 from `market_listing`, or returns a 404.
New listings get their id from SQLite when `listing_new` saves the form.

## Pages a logged-out visitor can open

The board (with the category filter), listing detail pages, register and sign in.
Everything else uses `login_required` and redirects to sign in.

## What the profile form writes back

First name, last name, email and `is_staff`. The `is_staff` checkbox was labelled
"Show my name on the department board".

## Department desk

It shows internal pickup info (hold closet location and a reimbursement code). Only
`is_staff` accounts should see it.

## Security defect

Any user can give themselves staff access:

1. Sign in as `alex` / `campus123`.
2. Open `/profile/`, tick "Show my name on the department board", save.
3. Open `/desk/`. The reimbursement code `DESK-2290` is shown.

The checkbox is really `is_staff`, which is the same flag the desk checks.

## Patch

Removed `is_staff` from `ProfileForm` fields in `market/forms.py`. The profile form now
only saves name and email, so users cannot make themselves staff. Staff accounts are
set by an admin. Posting, editing and messaging are unchanged.

For hosting on Render I added WhiteNoise for static files and `SECURE_PROXY_SSL_HEADER`
so sign-in works over HTTPS.
