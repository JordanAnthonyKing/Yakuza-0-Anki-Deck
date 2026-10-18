"""Pipeline wrapper: run verify_word_audio.py for one chapter in the ASR venv (tools/asr),
which carries faster-whisper + CUDA; the pipeline itself runs in .venv.

Usage: python scripts/audio/verify_stage.py <ch>
"""
import os, sys, subprocess

R = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
subprocess.run([os.path.join(R, "tools", "asr", "Scripts", "python.exe"),
                os.path.join(R, "scripts", "audio", "verify_word_audio.py"), *sys.argv[1:]], check=True)
