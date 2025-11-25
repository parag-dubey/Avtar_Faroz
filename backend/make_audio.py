import edge_tts
import asyncio

# Wahi same voice jo aapka Avatar use karta hai
VOICE = "en-IN-PrabhatNeural"

# Aapka chuna hua sentence
TEXT = "Just a moment, let me gather the details."

OUTPUT_FILE = "thinking.mp3"

async def main():
    print(f"🎤 Generating audio using {VOICE}...")
    communicate = edge_tts.Communicate(TEXT, VOICE)
    await communicate.save(OUTPUT_FILE)
    print(f"✅ Success! File saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())