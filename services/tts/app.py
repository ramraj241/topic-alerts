"""Edge TTS Service - Free text-to-speech API."""

import asyncio
import io
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

import edge_tts

app = FastAPI(title="Edge TTS Service", version="1.0.0")


class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-AriaNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "edge-tts"}


@app.get("/voices")
async def list_voices():
    """List available voices."""
    voices = await edge_tts.list_voices()
    english_voices = [v for v in voices if v["Locale"].startswith("en-")]
    return {
        "voices": [
            {"name": v["ShortName"], "gender": v["Gender"], "locale": v["Locale"]}
            for v in english_voices
        ]
    }


@app.post("/synthesize")
async def synthesize(request: TTSRequest):
    """Convert text to speech and return MP3 audio."""
    if not request.text or len(request.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if len(request.text) > 10000:
        raise HTTPException(status_code=400, detail="Text too long (max 10000 chars)")

    try:
        communicate = edge_tts.Communicate(
            request.text,
            request.voice,
            rate=request.rate,
            pitch=request.pitch,
        )

        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])

        audio_data.seek(0)
        return Response(
            content=audio_data.read(),
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"attachment; filename={uuid.uuid4()}.mp3"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
