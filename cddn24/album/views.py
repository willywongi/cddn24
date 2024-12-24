from django.conf import settings
from django.forms import Form, EmailField
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse

from album.models import Album
from album.tasks import build_album, TRACKS
from album.tokens import default_token_generator


class ClaimForm(Form):
    email = EmailField()

    def clean_email(self):
        return self.cleaned_data["email"].lower()


def claim(request):
    if request.method == "POST":
        form = ClaimForm(request.POST)
        if form.is_valid():
            album = Album.objects.claim(form.cleaned_data["email"])
            if album.status == Album.Status.IDLE:
                from album.tasks import send_validation_message
                send_validation_message.send(album.id, request.build_absolute_uri())
                return redirect("claimed", album.signature)

            return redirect("play", album.signature)

    else:
        form = ClaimForm()
    context = {
        "form": form,
        "total": Album.objects.count(),
        "claimed": Album.objects.filter(request_by__isnull=False).count(),
        "available": Album.objects.filter(request_by__isnull=True).count(),
        "is_available": Album.objects.filter(request_by__isnull=True).exists()
    }
    return TemplateResponse(request, "album/claim.html", context=context)


def claimed(request, signature):
    album = get_object_or_404(Album, signature=signature)
    context = {
        "seed": album.seed
    }
    return TemplateResponse(request, "album/claimed.html", context=context)


def validate(request, signature):
    album = get_object_or_404(Album, signature=signature)
    if album.status != Album.Status.IDLE:
        return redirect("play", album.signature)
    token = request.GET.get("token")
    if not default_token_generator.check_token(album, token):
        return redirect("not_valid", signature)
    build_album.send(album.seed)
    context = {
        "seed": album.seed,
    }
    return TemplateResponse(request, "album/validated.html", context)


def not_valid(request, signature):
    album = get_object_or_404(Album, signature=signature)
    return TemplateResponse(request, "album/not_valid.html", context={"album": album})


def read(request, signature):
    album = get_object_or_404(Album, signature=signature)
    if album.status == Album.Status.FINISHED:
        template = "album/read.html"
    else:
        template = "album/not_finished.html"

    tracks = [
        *[("meta/musicgen-large", title, prompt) for title, prompt in TRACKS],
        ("meta/llama3.3 e Elevenlabs", "Gianni e le prugne della Patagonia", "Scrivi un brevissimo racconto a tema natalizio con "
                                        "protagonista Gianni e le prugne della Patagonia. Lo stile "
                                        "deve essere sognante e surreale. Inizia con: \"Era la notte "
                                        "della vigilia di Natale...\"")
    ]

    context = {
        "has_error": album.error is not None,
        "seed": album.seed,
        "signature": album.signature,
        "cover_url": f"{settings.MEDIA_URL}/{album.path.relative_to(settings.MEDIA_ROOT)}/00_cover.png",
        "tracks": [{
            "no": i + 1,
            "title": title,
            "tool": tool,
            "url": f"{settings.MEDIA_URL}{path.relative_to(settings.MEDIA_ROOT)}",
            "prompt": prompt
        } for i, ((tool, title, prompt), path) in enumerate(zip(tracks, sorted(album.path.glob("*.mp3"))))]
    }
    return TemplateResponse(request, template, context)
