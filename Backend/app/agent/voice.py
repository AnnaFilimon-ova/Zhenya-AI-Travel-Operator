
from faster_whisper import WhisperModel
import edge_tts

_model = None


def get_model():
    global _model

    if _model is None:
        _model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8",
        )

    return _model


async def transcribe_audio(audio_path: str) -> str:
    """Распознаёт голосовое сообщение локально через faster-whisper."""
    import asyncio

    def transcribe():
        model = get_model()
        segments, _ = model.transcribe(
            audio_path,
            language="ru",
            beam_size=5,
            vad_filter=True,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()

    return await asyncio.to_thread(transcribe)


async def synthesize_speech(text: str, output_path: str) -> None:
    """Озвучивает ответ на русском языке."""
    communicator = edge_tts.Communicate(
        text=text,
        voice="ru-RU-SvetlanaNeural",
    )
    await communicator.save(output_path)
