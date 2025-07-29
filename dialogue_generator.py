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
        # Generate silence file directly in the correct format
        silence_file = os.path.join(temp_dir, "silence.mp3")
        subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", "0.2",
            "-acodec", "libmp3lame",
            "-ar", "44100", "-ac", "1", "-b:a", "128k",
            "-y", silence_file  # -y to overwrite if exists
        ], check=True, capture_output=True)

        # Verify the silence file was created correctly
        result = subprocess.run([
            "ffmpeg", "-i", silence_file
        ], capture_output=True, text=True)
        if "Invalid data found" in result.stderr:
            print("Error: Silence file not generated correctly. Trying alternative approach...")
            # Alternative silence generation
            subprocess.run([
                "ffmpeg", "-f", "lavfi",
                "-i", "sine=frequency=1:duration=0.2",
                "-af", "volume=-60dB",
                "-acodec", "libmp3lame",
                "-ar", "44100", "-ac", "1", "-b:a", "128k",
                "-y", silence_file
            ], check=True, capture_output=True)

        print("\nGenerating individual audio files for each turn...")
        # Generate individual audio files for each turn
        audio_files = []
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
        # Debug: Check each audio file's format
        for i, audio_file in enumerate(audio_files):
            print(f"\nChecking format of file {i+1}/{len(audio_files)}: {os.path.basename(audio_file)}")
            subprocess.run([
                "ffmpeg", "-i", audio_file
            ], capture_output=True, text=True)

        # Build the filter complex string for concatenation
        inputs = []
        filter_parts = []
        for i, audio_file in enumerate(audio_files):
            inputs.extend(["-i", audio_file])
            filter_parts.append(f"[{i}:a]")
        
        filter_complex = f"{''.join(filter_parts)}concat=n={len(audio_files)}:v=0:a=1[outa]"
        
        # Combine all audio files using filter complex
        output_path = f"audios/{target_word.replace(' ', '_')}.mp3"
        print("\nExecuting final concatenation...")
        cmd = [
            "ffmpeg",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-ac", "1",
            "-ar", "44100",
            "-b:a", "128k",
            output_path
        ]
        
        print("\nExecuting ffmpeg command:")
        print(" ".join(cmd))
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stderr:
            print("\nffmpeg stderr output:")
            print(result.stderr)
            
        if result.returncode != 0:
            print("\nError concatenating files. Trying alternative approach...")
            # Alternative approach: concatenate files one by one
            temp_output = os.path.join(temp_dir, "temp_output.mp3")
            # Copy first file as starting point
            subprocess.run(["cp", audio_files[0], temp_output], check=True)
            
            for i in range(1, len(audio_files)):
                next_temp = os.path.join(temp_dir, f"temp_output_{i}.mp3")
                filter_complex = f"[0:a][1:a]concat=n=2:v=0:a=1[outa]"
                result = subprocess.run([
                    "ffmpeg",
                    "-i", temp_output,
                    "-i", audio_files[i],
                    "-filter_complex", filter_complex,
                    "-map", "[outa]",
                    "-ac", "1",
                    "-ar", "44100",
                    "-b:a", "128k",
                    next_temp
                ], capture_output=True, text=True)
                if result.stderr:
                    print(f"\nffmpeg stderr for file {i+1}:")
                    print(result.stderr)
                subprocess.run(["mv", next_temp, temp_output], check=True)
            
            subprocess.run(["mv", temp_output, output_path], check=True)
        
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