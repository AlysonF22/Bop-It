import math
import array
import time
from machine import ADC, Pin, UART

# Global variables
in_arr = array.array('i', [0] * 128)
NoteV = bytearray([8, 23, 40, 57, 76, 96, 116, 138, 162, 187, 213, 241, 255])
f_peaks = array.array('f', [0] * 8)  # top 8 frequencies peaks in descending order

# Setup for Pi Pico
# Pi Pico has ADC on GPIO 26-29 (ADC0-ADC3) and internal temp sensor on ADC4
adc = ADC(Pin(26))  # Using ADC0 (GPIO26) - adjust as needed
uart = UART(0, baudrate=250000)  # UART0 on Pi Pico

def main():
    print("Chord Detection for Raspberry Pi Pico")
    print("Ready to detect chords...")
    
    while True:
        chord_det()
        time.sleep_ms(10)  # Small delay between detections

def chord_det():
    """Chord detection function"""
    sum1 = 0
    sum2 = 0
    
    # Start timing
    a1 = time.ticks_us()
    
    # Data collection with Hann window
    for i in range(128):
        # Pi Pico ADC is 12-bit (0-4095)
        a = adc.read_u16() >> 4  # Convert 16-bit to 12-bit (0-4095)
        a = a - 2048  # Zero shift for 12-bit ADC
        
        # Utilizing time between two samples for windowing & amplitude calculation
        sum1 += a  # To average value
        sum2 += a * a  # To RMS value
        a = a * (math.sin(i * math.pi / 128) * math.sin(i * math.pi / 128))  # Hann window
        in_arr[i] = int(4 * a)  # Scaling for float to int conversion
        time.sleep_us(195)  # Based on operation frequency range
    
    # End timing
    b = time.ticks_us()
    
    # Calculate amplitude and sampling frequency
    sum1 = sum1 / 128  # Average amplitude
    sum2 = math.sqrt(sum2 / 128)  # RMS amplitude
    sampling = 128000000 / time.ticks_diff(b, a1)  # Real time sampling frequency
    
    # For very low or no amplitude, this code won't start
    # It takes very small amplitude of sound to initiate for value sum2-sum1>3
    if sum2 - sum1 > 3:
        fft(128, sampling)  # Optimized FFT code
        
        # Clear first 12 positions in input array
        for i in range(12):
            in_arr[i] = 0
        
        j = 0
        k = 0
        # Below loop will convert frequency value to note
        for i in range(8):
            if f_peaks[i] > 1040:
                f_peaks[i] = 0
            if 65.4 <= f_peaks[i] <= 130.8:
                f_peaks[i] = 255 * ((f_peaks[i] / 65.4) - 1)
            if 130.8 <= f_peaks[i] <= 261.6:
                f_peaks[i] = 255 * ((f_peaks[i] / 130.8) - 1)
            if 261.6 <= f_peaks[i] <= 523.25:
                f_peaks[i] = 255 * ((f_peaks[i] / 261.6) - 1)
            if 523.25 <= f_peaks[i] <= 1046:
                f_peaks[i] = 255 * ((f_peaks[i] / 523.25) - 1)
            if 1046 <= f_peaks[i] <= 2093:
                f_peaks[i] = 255 * ((f_peaks[i] / 1046) - 1)
            if f_peaks[i] > 255:
                f_peaks[i] = 254
                
            j = 1
            k = 0
            while j == 1:
                if f_peaks[i] <= NoteV[k]:
                    f_peaks[i] = k
                    j = 0
                k += 1  # A note with max peaks (harmonic) with amplitude priority is selected
                if k > 15:
                    j = 0
            
            if f_peaks[i] == 12:
                f_peaks[i] = 0
            k = int(f_peaks[i])
            in_arr[k] = in_arr[k] + (8 - i)
        
        # Find note with maximum value
        k = 0
        j = 0
        for i in range(12):
            if k < in_arr[i]:
                k = in_arr[i]
                j = i
        
        # Copy first 8 values to positions 12-19
        for i in range(8):
            in_arr[12 + i] = in_arr[i]
        
        # Chord check
        for i in range(12):
            in_arr[20 + i] = in_arr[i] * in_arr[i + 4] * in_arr[i + 7]  # Major chord
            in_arr[32 + i] = in_arr[i] * in_arr[i + 3] * in_arr[i + 7]  # Minor chord
        
        # Find chord with max possibility
        for i in range(24):
            in_arr[i] = in_arr[i + 20]
            if k < in_arr[i]:
                k = in_arr[i]
                j = i
        
        # Major-minor check
        chord = j
        if chord > 11:
            chord = chord - 12
            chord_out = 'm'
        else:
            chord_out = ' '
        
        # Print detected chord
        k = chord
        chord_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        result = f"{chord_names[k]}{chord_out}"
        print(result)
        uart.write(result + '\n')  # Also output to UART

def fft(N, frequency):
    """FFT Function optimized for 128 sample size to reduce memory consumption"""
    data = [1, 2, 4, 8, 16, 32, 64, 128]
    a = N
    
    # Calculate the levels
    o = 7  # Hardcoded for N=128
    
    # Arrays for FFT calculation
    in_ps = array.array('B', [0] * data[o])  # Input for sequencing
    out_r = array.array('f', [0] * data[o])  # Real part of transform
    out_im = array.array('f', [0] * data[o])  # Imaginary part of transform
    
    x = 0
    # Bit reversal
    for b in range(o):
        c1 = data[b]
        f = data[o] // (c1 + c1)
        for j in range(c1):
            x = x + 1
            in_ps[x] = in_ps[j] + f
    
    # Update input array as per bit reverse order
    for i in range(data[o]):
        if in_ps[i] < a:
            out_r[i] = in_arr[in_ps[i]]
        if in_ps[i] > a:
            out_r[i] = in_arr[in_ps[i] - a]
    
    # FFT calculation
    for i in range(o):
        i10 = data[i]  # Overall values of sine cosine
        i11 = data[o] // data[i + 1]  # Loop with similar sine cosine
        e = 6.283 / data[i + 1]
        e = 0 - e
        n1 = 0
        
        for j in range(i10):
            c = math.cos(e * j)
            s = math.sin(e * j)
            n1 = j
            
            for k in range(i11):
                tr = c * out_r[i10 + n1] - s * out_im[i10 + n1]
                ti = s * out_r[i10 + n1] + c * out_im[i10 + n1]
                
                out_r[n1 + i10] = out_r[n1] - tr
                out_r[n1] = out_r[n1] + tr
                
                out_im[n1 + i10] = out_im[n1] - ti
                out_im[n1] = out_im[n1] + ti
                
                n1 = n1 + i10 + i10
    
    # Calculate amplitude from complex number
    for i in range(data[o - 1]):
        out_r[i] = math.sqrt((out_r[i] * out_r[i]) + (out_im[i] * out_im[i]))
        out_im[i] = (i * frequency) / data[o]  # Frequency bin
    
    # Peak detection
    x = 0
    for i in range(1, data[o - 1] - 1):
        if out_r[i] > out_r[i - 1] and out_r[i] > out_r[i + 1]:
            in_ps[x] = i  # in_ps array used for storage of peak number
            x = x + 1
    
    # Rearrange as per magnitude
    s = 0
    c = 0
    for i in range(x):
        for j in range(c, x):
            if out_r[in_ps[i]] < out_r[in_ps[j]]:
                s = in_ps[i]
                in_ps[i] = in_ps[j]
                in_ps[j] = s
        c = c + 1
    
    # Update f_peaks array with frequencies in descending order
    for i in range(8):
        if i < x:  # Make sure we have enough peaks
            # Weighted average of peak and adjacent bins for better frequency resolution
            f_peaks[i] = (out_im[in_ps[i] - 1] * out_r[in_ps[i] - 1] + 
                         out_im[in_ps[i]] * out_r[in_ps[i]] + 
                         out_im[in_ps[i] + 1] * out_r[in_ps[i] + 1]) / \
                        (out_r[in_ps[i] - 1] + out_r[in_ps[i]] + out_r[in_ps[i] + 1])
        else:
            f_peaks[i] = 0

# Run the main function
if __name__ == "__main__":
    main()
