import edge_tts
from groq import AsyncGroq
from app.config import settings

async def transcribe_audio(audio_path: str) -> str:
    """Convert a Telegram voice message to text using Groq Whisper."""
    if not settings.groq_api_key:
        raise RuntimeError("Groq API key not set")

    client = AsyncGroq(api_key=settings.groq_api_key)

    with open(audio_path, "rb") as audio_file:
        result = await client.audio.transcriptions.create(
            file=(audio_path.split("/")[-1], audio_file.read()),
            model="whisper-large-v3-turbo",
            response_format="json",
        )

    return result.text.split()

async def synthesize_speech(text: str, output_path: str) -> None:
    """Convert text to Russian speech."""
    communicator = edge_tts.Communicate(
        text=text,
        voice="ru-RU-SvetlanaNeural",
    )
    await communicator.save(output_path)