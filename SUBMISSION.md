# SwapShelf Assignment

**Student:** Beren Dogar  
**Hosted URL:** https://swapshelf-beren-dogar.onrender.com  
**Patched repository:** https://github.com/Berendogar/SwapShelf

## Architecture sketch

```text
Browser
  -> swapshelf/urls.py
  -> market/urls.py
  -> market/views.py
  -> market/forms.py (when a form is submitted)
  -> market/models.py
  -> data/swapshelf.db (SQLite)

The view renders a template from market/templates/market/.
```

SwapShelf is a server-rendered Django app. Django's auth app handles accounts and
sessions. The `market` app has the listings, message threads and messages. Data is
stored in one SQLite file.

## How a listing id becomes a row

`/listings/3/` matches `listings/<int:pk>/` in `market/urls.py`, so Django calls
`listing_detail(request, pk=3)`. The view runs `get_object_or_404(Listing, pk=3)`,
which selects the row with id 3 from the `market_listing` table and returns it as a
`Listing` object. If no row exists the visitor gets a 404. The object is rendered
with `detail.html`.

New ids come from SQLite. `listing_new` saves the form with the logged-in user as
the owner, the row is inserted and SQLite gives it the next integer primary key.

## Pages a logged-out visitor can open

- the board `/`, including the category filter (`/?category=books`)
- listing detail pages `/listings/<id>/`
- `/register/` and `/login/`
- the Django admin login page `/admin/` (nothing behind it without an admin account)

Posting, editing, Mine, messages, profile and the department desk use
`login_required`, so they redirect to the sign-in page.

## What the profile form writes back

In the original code `ProfileForm` was a ModelForm on Django's `User` with the
fields `first_name`, `last_name`, `email` and `is_staff`. The `is_staff` field was
relabelled "Show my name on the department board", so the checkbox looked like a
display setting but it saved the staff flag on the user row.

## Department desk

The desk shows internal department pickup information: the hold closet location
and a reimbursement code. It is meant only for department board accounts. The view
checks `request.user.is_staff`. Other signed-in users only see "This page is for
department board accounts."

## Security defect: any user can make themselves staff

Steps on the original code:

1. Sign in as `alex` / `campus123` (a normal account).
2. Open `/profile/`, tick "Show my name on the department board" and save.
3. A "Desk" link appears in the header. Open `/desk/`.
4. The page shows "Department hold closet, Hullihen basement cage B.
   Reimbursement code DESK-2290."

The checkbox posts `is_staff=on`, so the user grants themselves the permission the
desk checks. Since `is_staff` is also Django's admin flag, the account can also
sign in at `/admin/`, although it has no model permissions there.

## Patch

In `market/forms.py` I removed `is_staff` (and its label) from
`ProfileForm.Meta.fields`. The form now only saves first name, last name and email.
A ModelForm ignores POST fields that are not in `fields`, so sending `is_staff=on`
by hand does not work either. I also removed the sentence about the board flag from
`profile.html`.

Department board accounts now have to be set by an administrator in the Django
admin. The desk view did not need to change. Posting, editing, marking sold and
messaging are not affected.

Accounts that used the bug before the patch keep `is_staff`. On Render this does
not matter because the database is rebuilt on each deploy. On a persistent
database those accounts should be reset by an admin.

## Hosting

The app runs on Render with the existing Dockerfile (`render.yaml`). For hosting I
added WhiteNoise so the CSS is served, `SECURE_PROXY_SSL_HEADER` so Django knows
the request came in over HTTPS through Render's proxy (otherwise sign-in fails the
CSRF origin check), and gunicorn binds to the `PORT` Render provides.
