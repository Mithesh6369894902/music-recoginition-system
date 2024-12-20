import streamlit as st
import librosa
import numpy as np
import hashlib
import sqlite3
import matplotlib.pyplot as plt
from io import BytesIO

# Streamlit app configuration
st.set_page_config(page_title="Audio Fingerprint App", layout="wide")

# ---------------------------
# 1️⃣ Create the Spectrogram
# ---------------------------
def create_spectrogram(audio_file):
    """ Convert an audio file to a spectrogram. """
    y, sr = librosa.load(audio_file, sr=None)
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=2048, hop_length=512)
    S_db = librosa.power_to_db(S, ref=np.max)  # Convert to decibels
    return S_db, sr

# ---------------------------
# 2️⃣ Identify Peaks from Spectrogram
# ---------------------------
def get_peaks_from_spectrogram(spectrogram, threshold=-40):
    """ Identify the prominent peaks from the spectrogram. """
    peaks = []
    for time_index in range(spectrogram.shape[1]):
        for freq_index in range(spectrogram.shape[0]):
            if spectrogram[freq_index, time_index] > threshold:  # Threshold for prominent peaks
                peaks.append((time_index, freq_index))
    return peaks

# ---------------------------
# 3️⃣ Generate Unique Hashes for Peaks
# ---------------------------
def generate_hashes(peaks):
    """ Generate unique hashes from the peaks. """
    fingerprint_hashes = []
    for i in range(len(peaks) - 1):
        t1, f1 = peaks[i]
        t2, f2 = peaks[i + 1]
        hash_string = f"{f1}-{f2}-{t2 - t1}"
        fingerprint_hash = hashlib.sha256(hash_string.encode()).hexdigest()[:10]
        fingerprint_hashes.append(fingerprint_hash)
    return fingerprint_hashes

# ---------------------------
# 4️⃣ Store Fingerprints in Database
# ---------------------------
def store_fingerprints(song_name, hashes):
    """ Store the fingerprint hashes in a SQLite database. """
    conn = sqlite3.connect('fingerprints.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fingerprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_name TEXT,
            hash TEXT
        )
    ''')
    for hash_val in hashes:
        cursor.execute("INSERT INTO fingerprints (song_name, hash) VALUES (?, ?)", (song_name, hash_val))
    conn.commit()
    conn.close()

# ---------------------------
# 5️⃣ Identify Song from Database
# ---------------------------
def identify_song(hashes):
    """ Identify a song by matching the hashes to the database. """
    conn = sqlite3.connect('fingerprints.db')
    cursor = conn.cursor()
    matched_songs = {}
    for hash_val in hashes:
        cursor.execute("SELECT song_name FROM fingerprints WHERE hash = ?", (hash_val,))
        results = cursor.fetchall()
        for result in results:
            song_name = result[0]
            matched_songs[song_name] = matched_songs.get(song_name, 0) + 1

    conn.close()

    if matched_songs:
        most_likely_song = max(matched_songs, key=matched_songs.get)
        return f"🎉 Match found: {most_likely_song} (Confidence: {matched_songs[most_likely_song]} matches)"
    else:
        return "No match found."

# Streamlit App
st.title("Audio Fingerprint Web Application")
st.write("Upload an audio file to generate its fingerprint, store it in a database, and identify songs.")

# File Upload
uploaded_file = st.file_uploader("Upload an audio file (MP3/WAV)", type=["mp3", "wav"])
if uploaded_file:
    st.audio(uploaded_file, format="audio/mp3")
    
    # Generate Spectrogram
    with st.spinner("Generating spectrogram..."):
        spectrogram, sr = create_spectrogram(uploaded_file)
        fig, ax = plt.subplots(figsize=(10, 4))
        librosa.display.specshow(spectrogram, sr=sr, x_axis='time', y_axis='mel', cmap='coolwarm')
        plt.colorbar(format='%+2.0f dB')
        plt.title('Mel Spectrogram')
        plt.tight_layout()

        # Display Spectrogram
        st.pyplot(fig)
    
    # Extract Peaks
    with st.spinner("Extracting peaks..."):
        peaks = get_peaks_from_spectrogram(spectrogram)
        st.write(f"Total Peaks Detected: {len(peaks)}")

    # Generate Hashes
    with st.spinner("Generating hashes..."):
        hashes = generate_hashes(peaks)
        st.write(f"Total Hashes Generated: {len(hashes)}")
    
    # Store Fingerprints
    song_name = st.text_input("Enter song name to store fingerprints:")
    if st.button("Store Fingerprints"):
        if song_name:
            store_fingerprints(song_name, hashes)
            st.success("Fingerprints stored successfully!")
        else:
            st.error("Please enter a song name.")
    
    # Identify Song
    if st.button("Identify Song"):
        with st.spinner("Identifying song..."):
            result = identify_song(hashes)
            st.success(result)
