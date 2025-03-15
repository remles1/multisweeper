from django import forms
from django.core.exceptions import ValidationError


class LobbySettingsForm(forms.Form):
    mine_count = forms.ChoiceField(
        label='Mine Count',
        choices=[(i, i) for i in range(40, 65, 5)],
        required=True,
        widget=forms.Select()
    )

    max_players = forms.ChoiceField(
        label='Players',
        choices=[(i, i) for i in range(2, 7)],
        required=True,
        widget=forms.Select()
    )

    ranked = forms.BooleanField(
        label='Ranked Game',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_max_players(self):
        max_players = int(self.cleaned_data['max_players'])
        if max_players < 2 or max_players > 6:
            raise ValidationError("Max players must be between 2 and 6.")
        return max_players

    def clean_mine_count(self):
        mine_count = int(self.cleaned_data['mine_count'])
        if mine_count not in [i for i in range(40, 65, 5)]:
            raise ValidationError("Mine count must be between 40 and 60.")
        return mine_count

    def clean_ranked(self):
        ranked = self.cleaned_data['ranked']
        if not isinstance(ranked, bool):
            raise ValidationError("Ranked must be a boolean value.")
        return ranked

