from django.forms import ModelForm

from album.models import Album
from album.util import is_valid_hashtag


class AlbumForm(ModelForm):

    def is_valid(self):

        valid = super().is_valid()

        if not valid:
            return valid

        hashtag_valid, message = is_valid_hashtag(self.cleaned_data.get("hashtag"))

        if not hashtag_valid:
            self._errors["hashtag"] = message
            return False

        return True

    class Meta:
        model = Album
        fields = ['hashtag']
