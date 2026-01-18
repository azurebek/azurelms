from django import forms


class LeadCaptureForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Email manzilingiz",
            "autocomplete": "email",
        })
    )
    source = forms.CharField(required=False, widget=forms.HiddenInput())
