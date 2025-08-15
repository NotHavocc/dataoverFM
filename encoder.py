import wave
import math
import struct
from reedsolo import RSCodec
from colorama import Fore
import subprocess
import os

HANDSHAKE_START_HZ = 8192
HANDSHAKE_END_HZ = 8192 + 512

START_HZ = 1024
STEP_HZ = 300
BITS = 4

FEC_BYTES = 4
SAMPLE_RATE = 44100
TONE_DURATION = 0.1 

def encode_bitchunks(chunk_bits, byte_array):
    out_chunks = []
    for byte in byte_array:
        for i in range(0, 8, chunk_bits):
            chunk = (byte >> (8 - chunk_bits - i)) & ((1 << chunk_bits) - 1)
            out_chunks.append(chunk)
    return out_chunks

def generate_tone(freq, duration=TONE_DURATION, sample_rate=SAMPLE_RATE):
    samples = []
    for i in range(int(duration * sample_rate)):
        sample = math.sin(2 * math.pi * freq * (i / sample_rate))
        samples.append(sample)
    return samples

def normalize(samples):
    return b''.join(struct.pack('<h', int(s * 32767)) for s in samples)

def encode_message(message):
    rsc = RSCodec(FEC_BYTES)
    encoded_bytes = rsc.encode(message.encode("utf-8"))
    chunks = encode_bitchunks(BITS, encoded_bytes)
    freqs = [START_HZ + STEP_HZ * c for c in chunks]
    return [HANDSHAKE_START_HZ] + freqs + [HANDSHAKE_END_HZ]

def save_wav(filename, freqs):
    samples = []
    for f in freqs:
        samples.extend(generate_tone(f))
    pcm = normalize(samples)

    with wave.open(filename, 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm)

if __name__ == "__main__":
    print(Fore.BLUE + "DataOverFM encoder v1.1.0 by nothavoc (ported from pied-piper)")
    message = input(Fore.RESET + "Insert the text to encode: ")
    frequency = input("Insert the frequency to transmit on in MHz, from 76 to 108 (N to just save as .wav): ")
    if frequency.upper() == "N":
        print(Fore.GREEN + "N selected, will just save as .wav")
        filename = input(Fore.RESET + "Input a name for the file: ")
        print(Fore.MAGENTA + "Encoding:", message)
        audio = encode_message(message)
        save_wav(filename + ".wav", audio)
        print(Fore.GREEN + "Saved as "+ filename + ".wav")
        print(Fore.RESET)
    else:
        print(Fore.MAGENTA + "Encoding and transmitting at "+ frequency +"mHZ.")
        print("Encoding:", message)
        audio = encode_message(message)
        save_wav("temp.wav", audio)
        file_path = os.getcwd() + "/temp.wav"
        print("Press CTRL+C to stop.")
        try:
            result = subprocess.Popen([
                "sudo", "pi_fm_rds",
                "-freq", str(frequency), "-audio",
                file_path
            ], cwd=os.getcwd(), text=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            input("Press Enter to stop...\n")
            result.terminate()
            print(Fore.GREEN + "Success:", result.stdout)
            print(Fore.RESET)
        except subprocess.CalledProcessError as e:
            print(Fore.RED + "Error running PiFmRds:")
            print(Fore.RED + "Return code:", e.returncode)
            print(Fore.RED + "Output:", e.output)
            print(Fore.RED + "Error output:", e.stderr)
        except FileNotFoundError:
            print(Fore.RED + "PiFmRds binary not found! Did you build it and put it in PATH?")
        except Exception as e:
            print(Fore.RED + "Unexpected error:", e)
        os.remove("temp.wav")
        print(Fore.RESET)