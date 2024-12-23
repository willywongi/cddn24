from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AlbumValidateTokenGenerator(PasswordResetTokenGenerator):

    def _make_hash_value(self, album, timestamp):
        login_timestamp = (
            ""
            if album.updated_at is None
            else album.updated_at.replace(microsecond=0, tzinfo=None)
        )
        return f"{album.pk}{album.status}{login_timestamp}{timestamp}{album.seed}"


default_token_generator = AlbumValidateTokenGenerator()
