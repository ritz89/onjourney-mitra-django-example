import uuid

from django import forms


class BookingForm(forms.Form):
    start_at = forms.DateField(
        label="Tanggal keberangkatan",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    season_id = forms.ChoiceField(
        label="Jadwal keberangkatan",
        required=False,
        widget=forms.RadioSelect,
    )
    guest_no = forms.IntegerField(
        label="Jumlah tamu",
        min_value=1,
        initial=2,
        widget=forms.NumberInput(attrs={"min": 1, "inputmode": "numeric"}),
    )
    operation_id = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, product, departures, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product
        if product["is_seasonal"]:
            del self.fields["start_at"]
            self.fields["season_id"].choices = [
                (item["id"], item["tour_date"]) for item in departures
            ]
            self.fields["season_id"].required = True
        else:
            del self.fields["season_id"]
            self.fields["start_at"].required = True
        self.fields["guest_no"].widget.attrs["max"] = product["capacity"]
        self.initial.setdefault("operation_id", uuid.uuid4())
