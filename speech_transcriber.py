"""
MODULE: Speech Transcriber
Purpose: Record audio from microphone and transcribe using Gemini API

Provides:
- AudioRecorder: Record audio from microphone to WAV file
- SpeechTranscriber: Transcribe audio using Gemini API
- record_and_transcribe(): Convenience function for full flow
"""

import os
import tempfile
import asyncio
from pathlib import Path
from typing import Optional

# Audio recording
try:
    import sounddevice as sd
    import scipy.io.wavfile as wav
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("SPEECH: Warning - sounddevice/scipy not installed, audio recording disabled")

# Gemini API
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("SPEECH: Warning - google-generativeai not installed, transcription disabled")

from config import config


class AudioRecorder:
    """
    Records audio from microphone and saves to WAV file.
    Uses sounddevice for cross-platform microphone access.
    """
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """
        Initialize audio recorder.
        
        Args:
            sample_rate: Audio sample rate in Hz (16000 optimal for speech)
            channels: Number of audio channels (1 for mono)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.recordings_dir = Path("recordings")
        self.recordings_dir.mkdir(exist_ok=True)
    
    def record(self, duration: int = 10, output_path: Optional[str] = None) -> Optional[str]:
        """
        Record audio from microphone.
        
        Args:
            duration: Recording duration in seconds
            output_path: Optional output file path (auto-generated if not provided)
            
        Returns:
            Path to recorded WAV file, or None if recording failed
        """
        if not AUDIO_AVAILABLE:
            print("SPEECH: ✗ Audio recording not available (install sounddevice scipy)")
            return None
        
        if output_path is None:
            import time
            output_path = str(self.recordings_dir / f"voice_{int(time.time())}.wav")
        
        print(f"\n🎤 Recording for {duration} seconds... (speak now)")
        print("   Press Ctrl+C to stop early")
        
        try:
            # Record audio
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.int16
            )
            
            # Wait for recording to complete
            sd.wait()
            
            # Save to WAV file
            wav.write(output_path, self.sample_rate, recording)
            
            print(f"SPEECH: ✓ Recorded {duration}s to {output_path}")
            return output_path
            
        except KeyboardInterrupt:
            sd.stop()
            print("\nSPEECH: Recording stopped early")
            if len(recording) > 0:
                wav.write(output_path, self.sample_rate, recording)
                return output_path
            return None
        except Exception as e:
            print(f"SPEECH: ✗ Recording failed: {e}")
            return None
    
    async def record_async(self, duration: int = 10) -> Optional[str]:
        """Async wrapper for record() to use in async context."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.record, duration, None)


class SpeechTranscriber:
    """
    Transcribes audio files using Google Gemini API.
    Supports WAV, MP3, and other common audio formats.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize speech transcriber with Gemini API.
        
        Args:
            api_key: Gemini API key (uses config if not provided)
        """
        self.api_key = api_key or config.llm.gemini_api_key
        self.model_name = "gemini-2.0-flash"
        
        if GENAI_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"SPEECH: Initialized Gemini transcriber ({self.model_name})")
        else:
            self.model = None
            if not self.api_key:
                print("SPEECH: Warning - No Gemini API key configured")
    
    def transcribe(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcribed text, or None if transcription failed
        """
        if not GENAI_AVAILABLE:
            print("SPEECH: ✗ Transcription not available (install google-generativeai)")
            return None
        
        if not self.model:
            print("SPEECH: ✗ Gemini API not configured")
            return None
        
        if not os.path.exists(audio_path):
            print(f"SPEECH: ✗ Audio file not found: {audio_path}")
            return None
        
        print(f"SPEECH: Transcribing {audio_path}...")
        
        try:
            # Read audio file
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            
            # Determine MIME type based on extension
            ext = Path(audio_path).suffix.lower()
            mime_types = {
                ".wav": "audio/wav",
                ".mp3": "audio/mp3",
                ".m4a": "audio/m4a",
                ".ogg": "audio/ogg",
            }
            mime_type = mime_types.get(ext, "audio/wav")
            
            # Create audio part for Gemini
            audio_part = {
                "mime_type": mime_type,
                "data": audio_data
            }
            
            # Send to Gemini for transcription
            response = self.model.generate_content([
                "Transcribe this audio clip exactly as spoken. Return ONLY the transcribed text, nothing else.",
                audio_part
            ])
            
            transcribed_text = response.text.strip()
            print(f"SPEECH: ✓ Transcribed: \"{transcribed_text[:50]}...\"" if len(transcribed_text) > 50 else f"SPEECH: ✓ Transcribed: \"{transcribed_text}\"")
            
            return transcribed_text
            
        except Exception as e:
            print(f"SPEECH: ✗ Transcription failed: {e}")
            return None
    
    async def transcribe_async(self, audio_path: str) -> Optional[str]:
        """Async wrapper for transcribe() to use in async context."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.transcribe, audio_path)


async def record_and_transcribe(duration: int = 10) -> Optional[str]:
    """
    Convenience function to record audio and transcribe in one call.
    
    Args:
        duration: Recording duration in seconds
        
    Returns:
        Transcribed text, or None if failed
    """
    recorder = AudioRecorder()
    transcriber = SpeechTranscriber()
    
    # Record audio
    audio_path = await recorder.record_async(duration)
    if not audio_path:
        return None
    
    # Transcribe
    text = await transcriber.transcribe_async(audio_path)
    
    # Cleanup temp file
    try:
        os.remove(audio_path)
    except:
        pass
    
    return text


# Standalone test
if __name__ == "__main__":
    import asyncio
    
    async def test_speech():
        print("=" * 50)
        print("SPEECH TRANSCRIBER TEST")
        print("=" * 50)
        
        # Test 1: Check dependencies
        print("\n--- Dependency Check ---")
        print(f"Audio recording: {'✓ Available' if AUDIO_AVAILABLE else '✗ Not available'}")
        print(f"Gemini API: {'✓ Available' if GENAI_AVAILABLE else '✗ Not available'}")
        print(f"API Key: {'✓ Configured' if config.llm.gemini_api_key else '✗ Not configured'}")
        
        if not AUDIO_AVAILABLE or not GENAI_AVAILABLE:
            print("\n⚠️ Missing dependencies. Install with:")
            print("pip install sounddevice scipy google-generativeai")
            return
        
        # Test 2: Record and transcribe
        print("\n--- Recording Test (5 seconds) ---")
        text = await record_and_transcribe(duration=5)
        
        if text:
            print(f"\n✓ Full transcription: \"{text}\"")
        else:
            print("\n✗ Transcription failed")
        
        print("\nSPEECH: ✓ Test complete!")
    
    asyncio.run(test_speech())
