import os
import requests
import json
import time
import streamlit as st
from moviepy.editor import VideoFileClip
import soundfile as sf
import librosa
import numpy as np

### Set ROOT_DIR
ROOT_DIR = os.getcwd()
print(ROOT_DIR)

API_KEY = "YLbKyqzkET5SFMR37R7JiL4u2YdXQD3U"

def convert_video_to_audio(video_path):
    video = VideoFileClip(video_path)
    audio_path = "temp_audio.wav"
    video.audio.write_audiofile(audio_path)
    return audio_path

def normalize_audio(audio_path):
    y, sr = librosa.load(audio_path, sr=None)
    y = librosa.util.normalize(y)
    normalized_audio_path = "temp_normalized.wav"
    sf.write(normalized_audio_path, y, sr)
    return normalized_audio_path

def clean_audio(normalized_audio_path):
    y, sr = librosa.load(normalized_audio_path, sr=None)
    y_trimmed, _ = librosa.effects.trim(y)
    cleaned_audio_path = "temp_cleaned.wav"
    sf.write(cleaned_audio_path, y_trimmed, sr)
    return cleaned_audio_path

def upload_to_cleanvoice(cleaned_audio_path):
    url = 'https://api.cleanvoice.ai/v2/upload?filename=audio.wav'
    headers = {'X-API-Key': API_KEY}
    response = requests.post(url, headers=headers)
    signed_url = response.json()['signedUrl']
    with open(cleaned_audio_path, "rb") as file:
        requests.put(signed_url, data=file)
    return signed_url
 
def request_cleanvoice_processing(signed_url, config):
    api = "https://api.cleanvoice.ai/v2/edits"
    data = {
        "input": {
            "files": [signed_url],
            "config": config
        }
    }
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    response = requests.post(api, data=json.dumps(data), headers=headers)
    response_data = response.json()
    print("Response data:", response_data)  # Print the response data to understand its structure
    return response_data.get('id')

def poll_cleanvoice_status(id):
    status_endpoint = f"https://api.cleanvoice.ai/v2/edits/{id}"
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    
    # Display a spinner while polling
    with st.spinner("Processing in progress..."):
        while True:
            response = requests.get(status_endpoint, headers=headers)
            response.raise_for_status()
            data = response.json()
            status = data.get('status')
            progress = data.get('progress')
            if status in ['SUCCESS', 'FAILED']:
                return status, data
            else:
                # Do not print status, Streamlit will display spinner automatically
                time.sleep(5)
def main():
    st.title("Audio Processing App")

    uploaded_file = st.file_uploader("Upload an audio or video file", type=["mp4", "mov", "avi", "wav", "mp3"])

    if uploaded_file is not None:
        file_type = uploaded_file.type.split('/')[0]  # 'video' or 'audio'

        video_path = audio_path = None
        if file_type == 'video':
            st.write("Converting video to audio...")
            video_path = uploaded_file.name
            with open(video_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            audio_path = convert_video_to_audio(video_path)
            st.write("Audio extracted and saved to:", audio_path)
        else:
            st.write("Using uploaded audio file directly...")
            audio_path = uploaded_file.name
            with open(audio_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        st.write("Normalizing audio...")
        normalized_audio_path = normalize_audio(audio_path)
        st.write("Audio normalized and saved to:", normalized_audio_path)

        st.write("Cleaning audio...")
        cleaned_audio_path = clean_audio(normalized_audio_path)
        st.write("Audio cleaned and saved to:", cleaned_audio_path)

        st.write("Configure CleanVoice Processing Options:")
        long_silences = st.checkbox("Remove Long Silences", value=True)
        hesitations = st.checkbox("Remove Hesitations", value=True)
        mouth_sounds = st.checkbox("Remove Mouth Sounds", value=True)
        fillers = st.checkbox("Remove Fillers", value=True)
        remove_noise = st.checkbox("Remove Noise", value=True)
        normalize = st.checkbox("Normalize", value=True)
        stutters = st.checkbox("Remove Stutters", value=True)
        breath = st.checkbox("Remove Breaths", value=True)
        autoeq = st.checkbox("Auto EQ", value=True)

        config = {
            "long_silences": long_silences,
            "hesitations": hesitations,
            "mouth_sounds": mouth_sounds,
            "fillers": fillers,
            "remove_noise": remove_noise,
            "normalize": normalize,
            "stutters": stutters,
            "breath": breath,
            "autoeq": autoeq
        }

        if st.button("Start CleanVoice Processing"):
            st.write("Uploading to CleanVoice...")
            signed_url = upload_to_cleanvoice(cleaned_audio_path)
            st.write("Audio uploaded to CleanVoice.")

            st.write("Requesting CleanVoice processing...")
            id_value = request_cleanvoice_processing(signed_url, config)
            st.write("Processing ID:", id_value)

            st.write("Polling CleanVoice status...")
            status, response_data = poll_cleanvoice_status(id_value)

            if status == 'SUCCESS':
                result = response_data.get('result', {})
                download_url = result.get('download_url')
                st.write("Processing complete! Download your file here:")
                st.markdown(f"[Download processed audio]({download_url})")
            else:
                st.write("Processing failed. Please try again.")

if __name__ == "__main__":
    main()
