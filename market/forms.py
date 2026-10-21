from django.contrib.auth.models import User
from django import forms

from market.models import Listing, Profile


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ["title", "description", "price", "category", "seller_note"]


class ProfileForm(forms.ModelForm):
    show_on_department_board = forms.BooleanField(
        required=False,
        label="Show my name on the department board",
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            profile = Profile.objects.filter(user=self.instance).first()
            self.fields["show_on_department_board"].initial = bool(
                profile and profile.show_on_department_board
            )

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Profile.objects.update_or_create(
                user=user,
                defaults={
                    "show_on_department_board": self.cleaned_data[
                        "show_on_department_board"
                    ]
                },
            )
        return user
