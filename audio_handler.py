import edge_tts
import asyncio
import tempfile
from groq import Groq
import streamlit as st

groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio.flush()
        
        with open(temp_audio.name, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(temp_audio.name, file.read()),
                model="whisper-large-v3",
                response_format="text",
                language="en"
            )
    return transcription

async def generate_neural_voice(text):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        await communicate.save(temp_file.name)
        return temp_file.name

def get_audio_file(text):
    return asyncio.run(generate_neural_voice(text))
