from django import forms
from .models import Users


class LoginForm(forms.Form):
    email = forms.EmailField(label='이메일', widget=forms.EmailInput(
        attrs={'placeholder': 'jw.choi@example.com'}))
    password = forms.CharField(label='비밀번호', widget=forms.PasswordInput(
        attrs={'placeholder': '비밀번호 입력'}))
    remember = forms.BooleanField(label='로그인 상태 유지', required=False)


class SignupForm(forms.Form):
    nickname = forms.CharField(label='닉네임', widget=forms.TextInput(
        attrs={'placeholder': '사용하실 닉네임'}))
    email = forms.EmailField(label='이메일', widget=forms.EmailInput(
        attrs={'placeholder': 'jw.choi@example.com'}))
    password = forms.CharField(label='비밀번호', min_length=8, widget=forms.PasswordInput(
        attrs={'placeholder': '8자 이상 입력'}))
    password2 = forms.CharField(label='비밀번호 확인', min_length=8, widget=forms.PasswordInput(
        attrs={'placeholder': '비밀번호 재입력'}))
    agree = forms.BooleanField(label='이용약관 및 개인정보처리방침에 동의합니다')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password2'):
            raise forms.ValidationError('비밀번호가 일치하지 않습니다.')
        return cleaned

    def clean_email(self):
        email = self.cleaned_data['email']
        if Users.objects.filter(email=email).exists():
            raise forms.ValidationError('이미 가입된 이메일입니다.')
        return email