"""
DEV 4: VOICE MESSAGE TEST SCRIPT
Run this to test speech-to-text functionality independently

Usage: python dev4_test_voice.py

This tests audio recording and transcription without needing browser.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from config import config


async def test_dependencies():
    """Test that all required dependencies are installed."""
    print("=" * 60)
    print("DEV 4: VOICE MESSAGE TEST - DEPENDENCIES")
    print("=" * 60)
    
    # Test sounddevice
    try:
        import sounddevice as sd
        print(f"✓ sounddevice installed (version: {sd.__version__})")
        
        # List audio devices
        print("\n📢 Available audio input devices:")
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                print(f"   [{i}] {d['name']}")
    except ImportError as e:
        print(f"✗ sounddevice not installed: {e}")
        print("  Run: pip install sounddevice")
        return False
    
    # Test scipy
    try:
        import scipy
        print(f"\n✓ scipy installed (version: {scipy.__version__})")
    except ImportError as e:
        print(f"\n✗ scipy not installed: {e}")
        print("  Run: pip install scipy")
        return False
    
    # Test numpy
    try:
        import numpy as np
        print(f"✓ numpy installed (version: {np.__version__})")
    except ImportError as e:
        print(f"✗ numpy not installed: {e}")
        return False
    
    # Test google-generativeai
    try:
        import google.generativeai as genai
        print(f"✓ google-generativeai installed")
    except ImportError as e:
        print(f"\n✗ google-generativeai not installed: {e}")
        print("  Run: pip install google-generativeai")
        return False
    
    # Test Gemini API key
    if config.llm.gemini_api_key:
        print(f"✓ GEMINI_API_KEY configured ({config.llm.gemini_api_key[:8]}...)")
    else:
        print("\n⚠️ GEMINI_API_KEY not set in .env")
        print("  Transcription will fail without API key")
        return False
    
    print("\n✅ All dependencies available!")
    return True


async def test_audio_recording():
    """Test audio recording functionality."""
    print("\n" + "=" * 60)
    print("DEV 4: VOICE MESSAGE TEST - AUDIO RECORDING")
    print("=" * 60)
    
    try:
        from speech_transcriber import AudioRecorder, AUDIO_AVAILABLE
        
        if not AUDIO_AVAILABLE:
            print("✗ Audio recording not available")
            return None
        
        recorder = AudioRecorder()
        
        print("\n🎤 Recording 3 seconds of audio...")
        print("   (Speak something into your microphone)")
        
        audio_path = await recorder.record_async(duration=3)
        
        if audio_path:
            import os
            file_size = os.path.getsize(audio_path)
            print(f"\n✓ Recording saved: {audio_path}")
            print(f"   File size: {file_size} bytes")
            return audio_path
        else:
            print("\n✗ Recording failed")
            return None
            
    except Exception as e:
        print(f"\n✗ Recording error: {e}")
        return None


async def test_transcription(audio_path: str):
    """Test transcription functionality."""
    print("\n" + "=" * 60)
    print("DEV 4: VOICE MESSAGE TEST - TRANSCRIPTION")
    print("=" * 60)
    
    try:
        from speech_transcriber import SpeechTranscriber, GENAI_AVAILABLE
        
        if not GENAI_AVAILABLE:
            print("✗ Transcription not available")
            return None
        
        transcriber = SpeechTranscriber()
        
        print(f"\n🔄 Transcribing: {audio_path}")
        
        text = await transcriber.transcribe_async(audio_path)
        
        if text:
            print(f"\n✓ Transcription successful!")
            print(f"   Text: \"{text}\"")
            return text
        else:
            print("\n✗ Transcription failed")
            return None
            
    except Exception as e:
        print(f"\n✗ Transcription error: {e}")
        return None


async def test_full_flow():
    """Test the complete record → transcribe flow."""
    print("\n" + "=" * 60)
    print("DEV 4: VOICE MESSAGE TEST - FULL FLOW")
    print("=" * 60)
    
    try:
        from speech_transcriber import record_and_transcribe
        
        print("\n🎤 Testing complete voice message flow (5 seconds)...")
        print("   Speak a message like: 'Hi, is this still available?'")
        
        text = await record_and_transcribe(duration=5)
        
        if text:
            print(f"\n✓ Full flow successful!")
            print(f"   Final message: \"{text}\"")
            return True
        else:
            print("\n✗ Full flow failed")
            return False
            
    except Exception as e:
        print(f"\n✗ Full flow error: {e}")
        return False


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║  DEV 4: VOICE MESSAGE DEVELOPMENT                         ║
║                                                           ║
║  This script tests your speech-to-text implementation     ║
║  without needing browser or controller.                   ║
║                                                           ║
║  Focus areas:                                             ║
║  • Audio recording with sounddevice                       ║
║  • Transcription with Gemini API                          ║
║  • Complete record → transcribe flow                      ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    async def run_tests():
        # Test 1: Dependencies
        deps_ok = await test_dependencies()
        if not deps_ok:
            print("\n⚠️ Fix dependency issues before continuing")
            return
        
        # Test 2: Audio Recording
        audio_path = await test_audio_recording()
        if not audio_path:
            print("\n⚠️ Audio recording failed, skipping transcription test")
        else:
            # Test 3: Transcription
            await test_transcription(audio_path)
            
            # Cleanup
            try:
                import os
                os.remove(audio_path)
                print(f"\n🧹 Cleaned up: {audio_path}")
            except:
                pass
        
        # Test 4: Full Flow
        print("\n" + "-" * 60)
        print("Ready for full flow test? (This will record 5 seconds)")
        input("Press Enter to continue...")
        
        await test_full_flow()
        
        print("\n" + "=" * 60)
        print("🎉 ALL DEV 4 TESTS COMPLETE!")
        print("=" * 60)
    
    asyncio.run(run_tests())
