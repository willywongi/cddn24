import errno
import hashlib
import logging
import os
import traceback
from pathlib import Path
from typing import Optional

import dramatiq
import replicate
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage
from azure.ai.inference.models import UserMessage
from azure.core.credentials import AzureKeyCredential
from django.core.mail import send_mail, mail_admins
from django.template.loader import get_template
from django.contrib.staticfiles import finders
from django.urls import reverse
from elevenlabs import Voice, VoiceSettings
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment

from album.models import Album
from album.tokens import default_token_generator

VOICE_ID = "DLMxnwJE0a28JQLTMJPJ"  # Andy M

TRACKS = [
    ("Il Natale di Tim",
     "Moody and chill Christmas song, cinematic style, orchestral, with chimes, soft bells and whispering choirs, "
     "with a calm intro, a building up verse and chorus and a fading outro."),
    ("Non ascoltare questa canzone", "Contemporary pop song with bells and chimes as a Christmas song hit"),
    ("Never gonna Christmas up", "Power 80s pop track with catchy riffs with acoustic references to Christmas music, "
                                 "such as bells and chimes, and traditional melodies like Adeste fideles"),
    ("A.I.W.F.C.", "An Xmas song hit with heavy black metal riffs")
]
COVER_PROMPT = ("Three hooded figures in a snowy wood during a bright winter night, with a full moon peaking from the "
                "trees. Some of the trees are adorned with christmas decorations. The figures wear capes: we can't see "
                "their faces but the facial hair. The first figure is short and wears a goatee. Another wears a light "
                "beard and the last one just mustaches. The all composition in the style of a illustration for a "
                "Christmas album cover. On the top a writing in a futuristic font: \"CD DI NATALE 24\"")

logger = logging.getLogger("cddn24.album")


def pid_exists(pid):
    """Check whether pid exists in the current process table.
    UNIX only.
    """
    if pid < 0:
        return False
    if pid == 0:
        # According to "man 2 kill" PID 0 refers to every process
        # in the process group of the calling process.
        # On certain systems 0 is a valid PID but we have no way
        # to know that in a portable fashion.
        raise ValueError('invalid PID 0')
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH)
            raise
    else:
        return True


@dramatiq.actor(store_results=True)
def build_track(seed: int, track_no: int, title: str, prompt: str) -> Optional[Exception]:
    album = Album.objects.get(seed=seed)
    base_path = album.get_base_path()
    track_path = base_path / f"{track_no:02d} - {title}.mp3"
    lock_path = track_path.with_suffix(".lock")
    try:
        previous_pid = lock_path.read_text()
    except FileNotFoundError:
        previous_pid = None
    if previous_pid and not pid_exists(int(previous_pid)):
        previous_pid = None
        lock_path.unlink(missing_ok=True)

    if previous_pid:
        logger.warning("[%s] Track %s is already building", seed, track_no)
        return None

    if track_path.exists():
        logger.info("[%s] Track %s already exists", seed, track_no)
        return None

    lock_path.write_text(f"{os.getpid()}")
    exc = None
    try:
        logger.info("[%s] Track %s started", seed, track_no)
        output = replicate.run(
            "charlesmccarthy/musicgen:d51032695d2c2ec28031e9e30b793b1a8f61efe367af46027a211c2954a6ad44",
            input={
                "prompt": prompt,
                "duration": 60,
                "continuation": False,
                "model_version": "large",
                "output_format": "mp3",
                "multi_band_diffusion": True,
                "seed": album.seed
            }
        )
        with track_path.open("wb") as outfile:
            for data in output:
                outfile.write(data)
        logger.info("[%s] Track %s created", seed, track_no)
    except Exception as e:
        logger.exception("[%s] Track %s failed", seed, track_no)
        exc = e
    finally:
        lock_path.unlink()
    return exc


@dramatiq.actor(store_results=True)
def build_story(seed: int, track_no: int, title="Gianni e le prugne della Patagonia") -> Optional[Exception]:
    inference_client = ChatCompletionsClient(
        endpoint="https://models.inference.ai.azure.com",
        credential=AzureKeyCredential(os.environ["GITHUB_TOKEN"]),
    )
    tts_client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

    album = Album.objects.get(seed=seed)
    base_path = album.get_base_path()
    story_text_path = base_path / f"{track_no:02d} - {title}.txt"
    story_voice_path = base_path / f"{track_no:02d} - {title} - voce.mp3"
    story_track_path = base_path / f"{track_no:02d} - {title}.mp3"
    lock_path = story_track_path.with_suffix(".lock")
    try:
        previous_pid = lock_path.read_text()
    except FileNotFoundError:
        previous_pid = None
    if previous_pid and not pid_exists(int(previous_pid)):
        previous_pid = None
        lock_path.unlink(missing_ok=True)

    if previous_pid:
        logger.warning("[%s] Track %s (story) is already building", seed, track_no)
        return None

    lock_path.write_text(f"{os.getpid()}")
    exc = None
    logger.info("[%s] Track %s (story) started", seed, track_no)
    try:
        if story_text_path.exists():
            story_text = story_text_path.read_text()
        else:
            response = inference_client.complete(
                messages=[
                    SystemMessage(content="Sei un cantastorie sognante per bambini"),
                    UserMessage(content="Scrivi un brevissimo racconto a tema natalizio con "
                                        "protagonista Gianni e le prugne della Patagonia. Lo stile "
                                        "deve essere sognante e surreale. Inizia con: \"Era la notte "
                                        "della vigilia di Natale...\""),
                ],
                model="Llama-3.3-70B-Instruct",
                temperature=0.8,
                max_tokens=2048,
                top_p=0.1,
                seed=album.seed
            )
            story_text = response.choices[0].message.content
            with story_text_path.open("w") as outfile:
                outfile.write(story_text)
            logger.info("[%s] Track %s (story) text created", seed, track_no)

        if not story_voice_path.exists():
            audio = tts_client.generate(
                text=story_text,
                voice=Voice(
                    voice_id=VOICE_ID,
                    settings=VoiceSettings(stability=0.71, similarity_boost=0.5, style=0.0, use_speaker_boost=True)
                ),
                output_format="mp3_44100_64"
            )
            with story_voice_path.open("wb") as outfile:
                for chunk in audio:
                    outfile.write(chunk)
            logger.info("[%s] Track %s (story) voice created", seed, track_no)

        if not story_track_path.exists():
            voice_track = AudioSegment.from_mp3(story_voice_path)
            backing_track = AudioSegment.from_mp3(finders.find("story-backing-track.mp3"))
            if len(voice_track) < len(backing_track):
                backing_track = backing_track[:len(voice_track) + 5000]
            story_track = (backing_track - 4.5).overlay(voice_track, position=2500).fade_out(2500)
            story_track.export(story_track_path, format="mp3")
            story_voice_path.unlink(missing_ok=True)
            logger.info("[%s] Track %s (story) created", seed, track_no)
    except Exception as e:
        logger.exception("[%s] Track %s (story) failed", seed, track_no)
        exc = e
    finally:
        lock_path.unlink()
    return exc


@dramatiq.actor(store_results=True)
def build_cover(seed: int) -> Optional[Exception]:
    album = Album.objects.get(seed=seed)
    base_path = album.get_base_path()
    cover_path = base_path / f"00_cover.png"
    lock_path = cover_path.with_suffix(".lock")
    try:
        previous_pid = lock_path.read_text()
    except FileNotFoundError:
        previous_pid = None
    if previous_pid and not pid_exists(int(previous_pid)):
        previous_pid = None
        lock_path.unlink(missing_ok=True)

    if previous_pid:
        logger.warning("[%s] Cover is already building", seed)
        return None

    if cover_path.exists():
        logger.info("[%s] Cover already exists", seed)
        return None

    lock_path.write_text(f"{os.getpid()}")
    exc = None
    logger.info("[%s] Cover started", seed)
    try:
        output = replicate.run(
            "luma/photon",
            input={
                "seed": album.seed,
                "prompt": COVER_PROMPT,
                "aspect_ratio": "1:1",
                "image_reference_weight": 0.85,
                "style_reference_weight": 0.85
            }
        )
        with cover_path.open("wb") as outfile:
            for data in output:
                outfile.write(data)
        logger.info("[%s] Cover created", seed)
    except Exception as e:
        logger.exception("[%s] Build cover failed", seed)
        exc = e
    finally:
        lock_path.unlink()
    return exc


@dramatiq.actor
def build_album(seed: int, base_url: str, force=False):
    album = Album.objects.get(seed=seed)
    base_path = album.path
    base_path.mkdir(exist_ok=True)
    if album.status == Album.Status.FINISHED and album.error is not None:
        pass
    if album.status != Album.Status.IDLE and not force:
        logger.info("[%s] Build album request stopped: album is already worked on", album.seed)
        return
    album.status = Album.Status.RUNNING
    album.save()
    g = dramatiq.group([
        build_cover.message(album.seed),
        build_story.message(album.seed, len(TRACKS) + 1),
        *[build_track.message(album.seed, i + 1, title, prompt) for i, (title, prompt) in enumerate(TRACKS)]
    ]).run()

    album_errors = []
    for error in g.get_results(block=True, timeout=7 * 60 * 60 * 1000):
        if error:
            album_errors.append(f"{error}")

    if album_errors:
        album.error = "\n".join(album_errors)
        logger.error("[%s] Build album failed", seed)
    else:
        album.error = None
        logger.info("[%s] Build album completed", seed)
    album.status = Album.Status.FINISHED
    album.save()

    if album.error:
        mail_admins(f"Il CD di Natale 2024 {album.seed}: errore",
                    message=f"La registrazione del CD di Natale 2024 {album.seed} non è andata a buon fine:\n{album.error} ")
    else:
        play_urlpath = reverse("play", args=(album.signature,))
        send_mail(f"Il tuo CD di Natale 2024: {album.seed}",
                  "",
                  from_email=None,
                  recipient_list=[album.request_by],
                  fail_silently=False,
                  html_message=get_template("album/ready.mjml").render(
                      {"seed": album.seed, "play_url": f"{base_url.rstrip('/')}{play_urlpath}"}),
                  )


@dramatiq.actor
def send_validation_message(pk, base_url):
    album = Album.objects.get(pk=pk)
    validate_url = reverse("validate", args=(album.signature,))
    token = default_token_generator.make_token(album)
    context = {
        "signature": album.signature,
        "validate_url": f"{base_url.rstrip("/")}{validate_url}?token={token}",
        "seed": album.seed
    }
    send_mail(
        f"Il tuo CD di Natale 2024: {album.seed}",
        get_template("album/validate.mjml").render(context),
        from_email=None,
        recipient_list=[album.request_by],
        fail_silently=False,
        html_message=get_template("album/validate.mjml").render(context),
    )
