import os
import json
from pathlib import Path
from typing import List, Dict
import openai
import requests
from dotenv import load_dotenv
import tempfile
import subprocess

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Voice IDs for two different speakers
VOICE_IDS = {
    "A": "21m00Tcm4TlvDq8ikWAM",  # Replace with your preferred voice ID
    "B": "TX3LPaxmHKxFdv7VOQHJ"   # Replace with your preferred voice ID
}

def ensure_audio_directory():
    """Create audios directory if it doesn't exist."""
    Path("audios").mkdir(exist_ok=True)

def generate_dialogue(target_word: str) -> List[Dict[str, str]]:
    """Generate a dialogue using OpenAI that naturally incorporates the target word."""
    system_prompt = """
    You are a dialogue writer. Create a short, natural dialogue (2-5 turns) between two people (A and B).
    The dialogue should naturally incorporate the given target word without explicitly explaining it.
    Return ONLY a JSON array of objects, each with 'speaker' and 'text' keys.
    Keep the dialogue casual and relatable, ensuring it flows naturally when spoken.
    Example format:
    [
        {"speaker": "A", "text": "Hey, did you hear about the new app?"},
        {"speaker": "B", "text": "No, what's it about?"}
    ]
    """
    
    user_prompt = f"""
    Target word: "{target_word}"
    Requirements:
    - Use speakers A and B
    - Include the word naturally in context
    - Keep it conversational and realistic
    - Maximum 5 turns
    - Make sure the dialogue flows well when spoken
    - Return ONLY the JSON array, no other text
    """

    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        raise ValueError("Failed to parse OpenAI response as JSON. Response: " + response.choices[0].message.content)

def create_audio_dialogue(dialogue: List[Dict[str, str]], target_word: str):
    """Convert dialogue to speech using ElevenLabs API."""
    # Create a temporary directory for intermediate files
    with tempfile.TemporaryDirectory() as temp_dir:
        print("\nCreating silence file...")
        # Generate individual audio files for each turn
        audio_files = []
        silence_file = os.path.join(temp_dir, "silence.mp3")
        
        # Create a 1-second silence file
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", 
            "-t", "1", "-q:a", "0", "-map", "0", silence_file
        ], check=True, capture_output=True)
        
        for i, turn in enumerate(dialogue):
            print(f"\nGenerating audio for turn {i+1}/{len(dialogue)} (Speaker {turn['speaker']})...")
            print(f"Text: {turn['text']}")
            # Generate speech for this turn
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_IDS[turn['speaker']]}",
                headers={
                    "xi-api-key": os.getenv("ELEVEN_API_KEY"),
                    "Content-Type": "application/json",
                },
                json={
                    "text": turn["text"],
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                },
            )
            
            if response.status_code != 200:
                print(f"Error from ElevenLabs API: Status {response.status_code}")
                print("Response:", response.text)
                raise Exception(f"Failed to generate audio for speaker {turn['speaker']}")
            
            # Save the audio response to a temporary file
            temp_file = os.path.join(temp_dir, f"turn_{i}.mp3")
            with open(temp_file, "wb") as f:
                f.write(response.content)
            print(f"Audio generated successfully for turn {i+1}")
            
            # Add both the audio file and silence to our list
            audio_files.append(temp_file)
            if i < len(dialogue) - 1:  # Don't add silence after the last turn
                audio_files.append(silence_file)
        
        print("\nCombining audio files...")
        # Create a file list for ffmpeg
        list_file = os.path.join(temp_dir, "files.txt")
        with open(list_file, "w") as f:
            for audio_file in audio_files:
                f.write(f"file '{audio_file}'\n")
        
        # Combine all audio files
        output_path = f"audios/{target_word.replace(' ', '_')}.mp3"
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file,
            "-c", "copy", output_path
        ], check=True, capture_output=True)
        
        print(f"\nSaved combined audio file to {output_path}")
        return output_path

def main(target_word: str):
    """Main function to generate and save dialogue."""
    ensure_audio_directory()
    
    print(f"\nGenerating dialogue for target word: {target_word}")
    print("Waiting for GPT-4 response...")
    dialogue = generate_dialogue(target_word)
    
    print("\nGenerated Dialogue:")
    for turn in dialogue:
        print(f"{turn['speaker']}: {turn['text']}")
    
    print("\nStarting text-to-speech conversion...")
    output_path = create_audio_dialogue(dialogue, target_word)
    print(f"\nProcess completed! Audio saved to: {output_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python dialogue_generator.py <target_word>")
        sys.exit(1)
    
    main(sys.argv[1])