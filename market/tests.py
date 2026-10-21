from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from market.models import Listing, Message, Profile, Thread


class PublicPageTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="test-pass")
        self.listing = Listing.objects.create(
            owner=self.owner,
            title="Calculator",
            description="Used for one semester.",
            price="15.00",
            category="electronics",
        )

    def test_logged_out_visitor_can_open_public_pages(self):
        urls = [
            reverse("home"),
            reverse("listing_detail", args=[self.listing.pk]),
            reverse("sign_in"),
            reverse("register"),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_removed_listing_is_not_public(self):
        self.listing.status = "removed"
        self.listing.save(update_fields=["status"])

        response = self.client.get(reverse("listing_detail", args=[self.listing.pk]))

        self.assertEqual(response.status_code, 404)

    def test_logged_out_visitor_is_redirected_from_private_pages(self):
        urls = [reverse("listing_new"), reverse("mine"), reverse("profile"), reverse("desk")]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("sign_in"), response.url)


class ProfileSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", password="test-pass")
        self.client.force_login(self.user)

    def test_department_board_choice_does_not_grant_staff_access(self):
        response = self.client.post(
            reverse("profile"),
            {
                "first_name": "Beren",
                "last_name": "Dogar",
                "email": "beren@example.edu",
                "show_on_department_board": "on",
                "is_staff": "on",
            },
        )

        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertTrue(
            Profile.objects.get(user=self.user).show_on_department_board
        )
        self.assertEqual(self.client.get(reverse("desk")).status_code, 403)

    def test_profile_updates_normal_user_fields(self):
        self.client.post(
            reverse("profile"),
            {
                "first_name": "Beren",
                "last_name": "Dogar",
                "email": "beren@example.edu",
            },
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Beren")
        self.assertEqual(self.user.last_name, "Dogar")
        self.assertEqual(self.user.email, "beren@example.edu")

    def test_staff_account_can_open_department_desk(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

        response = self.client.get(reverse("desk"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DESK-2290")


class ObjectAuthorizationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="seller", password="test-pass")
        self.other_user = User.objects.create_user(username="buyer", password="test-pass")
        self.outsider = User.objects.create_user(username="outsider", password="test-pass")
        self.listing = Listing.objects.create(
            owner=self.owner,
            title="Course book",
            description="No missing pages.",
            price="20.00",
            category="books",
        )

    def test_signed_in_user_can_post_a_listing(self):
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse("listing_new"),
            {
                "title": "USB-C cable",
                "description": "One meter, working.",
                "price": "5.00",
                "category": "electronics",
                "seller_note": "Meet outside the library.",
            },
        )

        listing = Listing.objects.get(title="USB-C cable")
        self.assertRedirects(response, reverse("listing_detail", args=[listing.pk]))
        self.assertEqual(listing.owner, self.other_user)

    def test_non_owner_cannot_edit_or_mark_listing_sold(self):
        self.client.force_login(self.other_user)

        edit_response = self.client.get(reverse("listing_edit", args=[self.listing.pk]))
        sold_response = self.client.post(reverse("listing_sold", args=[self.listing.pk]))

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(sold_response.status_code, 404)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, "available")

    def test_owner_can_edit_and_mark_listing_sold(self):
        self.client.force_login(self.owner)
        edit_response = self.client.post(
            reverse("listing_edit", args=[self.listing.pk]),
            {
                "title": "Course book, second edition",
                "description": self.listing.description,
                "price": "18.00",
                "category": "books",
                "seller_note": "Meet at the library.",
            },
        )
        sold_response = self.client.post(reverse("listing_sold", args=[self.listing.pk]))

        self.assertEqual(edit_response.status_code, 302)
        self.assertEqual(sold_response.status_code, 302)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, "Course book, second edition")
        self.assertEqual(self.listing.status, "sold")

    def test_outsider_cannot_read_or_post_to_thread(self):
        thread = Thread.objects.create(listing=self.listing, buyer=self.other_user)
        Message.objects.create(thread=thread, sender=self.other_user, body="Is it available?")
        self.client.force_login(self.outsider)

        get_response = self.client.get(reverse("thread_detail", args=[thread.pk]))
        post_response = self.client.post(
            reverse("thread_detail", args=[thread.pk]), {"body": "I should not be here"}
        )

        self.assertEqual(get_response.status_code, 404)
        self.assertEqual(post_response.status_code, 404)
        self.assertEqual(thread.messages.count(), 1)

    def test_buyer_and_seller_can_use_thread(self):
        thread = Thread.objects.create(listing=self.listing, buyer=self.other_user)

        for user in (self.other_user, self.owner):
            with self.subTest(username=user.username):
                self.client.force_login(user)
                self.assertEqual(
                    self.client.get(reverse("thread_detail", args=[thread.pk])).status_code,
                    200,
                )

