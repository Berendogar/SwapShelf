# SwapShelf Assignment

**Student:** Beren Dogar  
**Hosted URL:** https://swapshelf-beren-dogar.onrender.com  
**Patched repository:** https://github.com/Berendogar/SwapShelf

## Short architecture sketch

```text
Browser
  -> swapshelf/urls.py
  -> market/urls.py
  -> market/views.py
  -> market/forms.py (when a form is submitted)
  -> market/models.py
  -> data/swapshelf.db

The view sends the result to a template in market/templates/market/.
```

This is a server-rendered Django application. Django handles login and sessions. The
`market` app contains the listings, message threads and messages. SQLite keeps the
data, so there is no separate database server.

## How a listing id becomes a row

When a listing is created, `listing_new` validates `ListingForm`, adds the logged-in
user as the owner and calls `listing.save()`. SQLite inserts a row into
`market_listing` and creates its integer primary key automatically.

For example, `/listings/3/` matches `<int:pk>` in `market/urls.py`. Django passes
`pk=3` to `listing_detail`. `get_object_or_404(Listing, pk=pk)` asks the ORM for the
row whose primary key is 3. Django turns that row into a `Listing` object, or returns
a 404 page if it does not exist. The object is then rendered by `detail.html`.

## Pages available without signing in

A logged-out visitor can open the public board (`/`), use its category query string,
open a listing detail page (`/listings/<id>/`), register (`/register/`) and sign in
(`/login/`). The Django admin login page is also reachable, but its contents still
require an admin account. Posting, editing, the Mine page, profiles, messages and the
department desk redirect to sign-in because their views use `login_required`.

In the original code the detail page also opened removed listings if you typed their
id. Removed listings now return 404.

## Profile form

In the original code the profile form wrote first name, last name, email and
`is_staff` back to Django's `User` row. The “Show my name on the department board”
checkbox was really `is_staff`.

After the patch the form writes only first name, last name and email to `User`. The
board choice is stored separately in the one-to-one `Profile` row. It is a display
preference and does not give the user any permission.

## Department desk

The desk contains internal department pickup information, including the hold-closet
location and reimbursement code. A visitor must be signed in and must already have
Django's `is_staff` permission. A normal signed-in user receives HTTP 403. Staff
status must be assigned by an administrator; it cannot be selected on the profile
page. The hosted demo has no staff account, so the allowed case is checked in the
tests.

## Security defect and reproduction

I found a privilege-escalation problem in the original profile form. The form showed
a harmless-sounding department-board checkbox, but the checkbox was actually the
Django `User.is_staff` field. The desk view trusted that same field.

I reproduced it in the original version like this:

1. Sign in as a normal demo user such as `alex`.
2. Open `/profile/`.
3. Check “Show my name on the department board” and save.
4. Open `/desk/`.
5. The normal account can now read the private location and the `DESK-2290` code.

The profile POST changed `is_staff` from false to true, so this was not only a hidden
link problem. Typing the desk URL directly also worked after changing the checkbox.
Because `is_staff` is also the Django admin flag, the same account could sign in at
`/admin/`. It had no model permissions there, so it could not change data.

## Patch

I replaced the form's direct `is_staff` field with
`Profile.show_on_department_board`. Saving the profile now updates only the user's
name, email and this separate preference. The desk still checks `is_staff`, but a
user can no longer grant that permission to themselves. Non-staff requests return
403 and staff accounts can still use the page.

The patch does not take `is_staff` away from accounts that already used the bug. On
Render the free database is rebuilt on every deploy, so this does not matter there.
On a server that keeps its database, staff accounts that are not superusers should be
checked by hand after deploying.

While checking access control, I also found that any signed-in account could open,
edit or mark sold another seller's listing by changing the id in the URL. The original
detail page even showed the Edit and Mark sold buttons to everyone. Opening the edit
page was enough to read the private seller note. For example, signed in as `sam`,
`/listings/1/edit/` showed Alex's note with locker 14 and the code `SWAP-7741`. A
guessed thread id could also expose its messages, for example `/threads/1/` between
Alex and Jordan. The listing views now load only objects owned by the current seller,
and the thread view only loads a thread for its buyer or seller. The page also hides
seller controls from other users. Normal posting and messaging are unchanged.

## Verification

Run the checks from the project directory:

```bash
python manage.py migrate
python manage.py test
PRODUCTION=1 SECRET_KEY='use-a-long-random-value' \
  ALLOWED_HOSTS='your-hostname.example' python manage.py check --deploy
```

The tests cover the public/private page split, removed listings, normal profile
updates, the failed privilege-escalation attempt, staff desk access, listing ownership
and thread participants.
