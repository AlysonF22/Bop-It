import math
import array
import time
from machine import ADC, Pin, UART
from ulab import numpy as np
from ulab import utils as utools # Newer versions of ulab use this for spectrograms

# Global variables
in_arr = array.array('f', [0] * 128)
NoteV = bytearray([8, 23, 40, 57, 76, 96, 116, 138, 162, 187, 213, 241, 255])
f_peaks = array.array('f', [0] * 8)  # Top 8 frequency peaks in descending order

# Setup for Pi Pico
adc = ADC(Pin(26))  # Using ADC0 (GPIO26)
uart = UART(0, baudrate=250000)  # UART0 on Pi Pico

# Precompute Hann window for efficiency
hann_window = np.array([math.sin(i * math.pi / 128)**2 for i in range(128)])


def main():
    print("Chord Detection for Raspberry Pi Pico")
    print("Ready to detect chords...")

    while True:
        detect_chord()
        time.sleep_ms(100)  # Small delay between detections


def detect_chord():
    """Detects musical chords using FFT and peak frequency detection."""
    start_time = time.ticks_us()

    sum1 = 0
    sum2 = 0

    # Collect samples and apply Hann window
    for i in range(128):
        sample = (adc.read_u16() >> 4) - 2048  # Convert to 12-bit and zero-center
        sum1 += sample
        sum2 += sample * sample
        in_arr[i] = sample * hann_window[i]

        time.sleep_us(195)  # Adjust sampling delay

    end_time = time.ticks_us()

    # Calculate RMS amplitude and sampling rate
    avg_amplitude = sum1 / 128
    rms_amplitude = math.sqrt(sum2 / 128)
    sampling_rate = 128000000 / time.ticks_diff(end_time, start_time)

    # Ignore weak signals
    if rms_amplitude - avg_amplitude <= 3:
        return

    # Convert input array to numpy and compute FFT
    signal = np.array(in_arr)
    spectrum = np.fft.fft(signal)
    magnitudes = abs(spectrum[:len(spectrum) // 2])  # Only take positive frequencies

    # Frequency bins
    freqs = np.linspace(0, sampling_rate / 2, len(magnitudes))

    # Detect peaks
    peak_indices = [
        (i, magnitudes[i])
        for i in range(1, len(magnitudes) - 1)
        if magnitudes[i] > magnitudes[i - 1] and magnitudes[i] > magnitudes[i + 1] and i > 2
    ]

    # Sort peaks by magnitude (descending)
    peak_indices.sort(key=lambda x: x[1], reverse=True)

    # Extract the top 8 peaks
    num_peaks = min(8, len(peak_indices))
    for i in range(8):
        f_peaks[i] = 0

    for i in range(num_peaks):
        idx = peak_indices[i][0]
        # Parabolic interpolation for better frequency estimation
        if 0 < idx < len(magnitudes) - 1:
            peak_pos = idx + 0.5 * (magnitudes[idx - 1] - magnitudes[idx + 1]) / (
                magnitudes[idx - 1] - 2 * magnitudes[idx] + magnitudes[idx + 1]
            )
            f_peaks[i] = freqs[int(peak_pos)]

    # Convert frequencies to notes
    note_arr = array.array('i', [0] * 12)

    for i in range(num_peaks):
        freq = f_peaks[i]
        if freq <= 0 or freq > 1040:
            continue

        # Normalize frequency into a 0-255 scale
        base_freqs = [65.4, 130.8, 261.6, 523.25, 1046]
        norm_freq = None

        for base in base_freqs:
            if base <= freq <= base * 2:
                norm_freq = (freq / base - 1) * 255
                break

        if norm_freq is None or norm_freq > 255:
            continue

        # Determine note index
        note_idx = next((j for j in range(len(NoteV)) if norm_freq <= NoteV[j]))

        # Assign weight to detected notes
        note_arr[note_idx % 12] += (8 - i)  # Stronger peaks get higher weight

    # Detect chords
    chord_name = detect_chord_from_notes(note_arr)
    print(chord_name)
    uart.write(chord_name + "\n")


def detect_chord_from_notes(note_arr):
    """Detects a chord based on detected note frequencies."""
    major_chords = array.array('i', [0] * 12)
    minor_chords = array.array('i', [0] * 12)

    # Major and minor chord detection
    for i in range(12):
        major_chords[i] = note_arr[i] * note_arr[(i + 4) % 12] * note_arr[(i + 7) % 12]
        minor_chords[i] = note_arr[i] * note_arr[(i + 3) % 12] * note_arr[(i + 7) % 12]

    # Find strongest chord match
    max_val = 0
    chord_idx = 0
    is_minor = False

    for i in range(12):
        if major_chords[i] > max_val:
            max_val = major_chords[i]
            chord_idx = i
            is_minor = False
        if minor_chords[i] > max_val:
            max_val = minor_chords[i]
            chord_idx = i
            is_minor = True

    # Chord names
    chord_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    chord_type = 'm' if is_minor else ''
    return f"{chord_names[chord_idx]}{chord_type}"


# Run the main function
if __name__ == "__main__":
    main()
