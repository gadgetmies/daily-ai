#!/usr/bin/env python3
"""Turn an episode script into a mastered mp3 using Kokoro-82M (local neural TTS).

Usage:  python3 scripts/synth.py script.txt out.mp3 [--voice bf_emma] [--speed 1.0]

The input is plain text. Blank lines separate paragraphs and become short
pauses. Kokoro has a per-call token limit, so paragraphs are further split on
sentence boundaries into chunks of roughly CHUNK_CHARS characters.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

MODEL_DIR = os.environ.get("MODEL_DIR", "/tmp/kokoro")
CHUNK_CHARS = 350
PARA_GAP = 0.45   # seconds of silence between paragraphs
CHUNK_GAP = 0.12  # seconds between chunks inside a paragraph


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def chunk_paragraph(para):
    """Group sentences into chunks that stay under the model's token budget."""
    chunks, cur = [], ""
    for sent in split_sentences(para):
        if len(sent) > CHUNK_CHARS:
            # A single runaway sentence: break it on commas rather than mid-word.
            if cur:
                chunks.append(cur)
                cur = ""
            piece = ""
            for frag in re.split(r"(?<=,)\s+", sent):
                if len(piece) + len(frag) + 1 > CHUNK_CHARS and piece:
                    chunks.append(piece)
                    piece = frag
                else:
                    piece = f"{piece} {frag}".strip()
            if piece:
                chunks.append(piece)
        elif len(cur) + len(sent) + 1 > CHUNK_CHARS and cur:
            chunks.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def synthesize(text, voice, speed):
    kokoro = Kokoro(
        os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"),
        os.path.join(MODEL_DIR, "voices-v1.0.bin"),
    )
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        sys.exit("empty script")

    pieces, rate = [], None
    for i, para in enumerate(paragraphs):
        for j, chunk in enumerate(chunk_paragraph(para)):
            samples, rate = kokoro.create(chunk, voice=voice, speed=speed, lang="en-gb")
            if j:
                pieces.append(np.zeros(int(CHUNK_GAP * rate), dtype=samples.dtype))
            pieces.append(samples)
        if i != len(paragraphs) - 1:
            pieces.append(np.zeros(int(PARA_GAP * rate), dtype=pieces[-1].dtype))

    return np.concatenate(pieces), rate


def master(wav_path, mp3_path):
    """Same chain the round-up already used: clean up, even out, normalise."""
    chain = (
        "highpass=f=70,"
        "acompressor=threshold=-18dB:ratio=3:attack=10:release=180,"
        "equalizer=f=3000:t=q:w=1.2:g=2,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,"
        "afade=t=in:d=0.2"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", wav_path,
         "-af", chain, "-codec:a", "libmp3lame", "-b:a", "128k",
         "-ar", "44100", "-ac", "1", mp3_path],
        check=True,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--voice", default="bf_emma")
    ap.add_argument("--speed", type=float, default=1.0)
    args = ap.parse_args()

    with open(args.script, encoding="utf-8") as fh:
        text = fh.read()

    samples, rate = synthesize(text, args.voice, args.speed)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        sf.write(tmp.name, samples, rate)
        master(tmp.name, args.out)
    os.unlink(tmp.name)

    seconds = len(samples) / rate
    print(f"{args.out}  {seconds:.1f}s  voice={args.voice}")


if __name__ == "__main__":
    main()
