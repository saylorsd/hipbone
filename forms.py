from django import forms

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class AddressForm(forms.Form):
    address = forms.CharField(max_length=255)
