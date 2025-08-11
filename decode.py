from __future__ import print_function

import sys
import wave
import io

import sounddevice as sd
import colorama
import numpy as np

from reedsolo import RSCodec, ReedSolomonError
from termcolor import cprint
from pyfiglet import figlet_format

# must match encoder settings
HANDSHAKE_START_HZ = 8192
HANDSHAKE_END_HZ = 8192 + 512

START_HZ = 1024
STEP_HZ = 300
BITS = 4

FEC_BYTES = 4


def stereo_to_mono(input_file):
    inp = wave.open(input_file, 'rb')
    params = list(inp.getparams())
    params[0] = 1  
    params[3] = 0 

    out_io = io.BytesIO()
    out = wave.open(out_io, 'wb')
    out.setparams(tuple(params))

    frames = inp.readframes(inp.getnframes())
    data = np.frombuffer(frames, dtype=np.int16)
    left = data[0::2]
    out.writeframes(left.tobytes())

    inp.close()
    out.close()
    out_io.seek(0)
    return out_io


def yield_chunks(input_file, interval):
    wav = wave.open(input_file, 'rb')
    frame_rate = wav.getframerate()

    chunk_size = int(round(frame_rate * interval))
    while True:
        chunk = wav.readframes(chunk_size)
        if not chunk:
            return
        yield frame_rate, np.frombuffer(chunk, dtype=np.int16)


def dominant(frame_rate, chunk):
    w = np.fft.fft(chunk)
    freqs = np.fft.fftfreq(len(chunk))
    peak_coeff = np.argmax(np.abs(w))
    peak_freq = freqs[peak_coeff]
    return abs(peak_freq * frame_rate)


def match(freq1, freq2):
    return abs(freq1 - freq2) < 20


def decode_bitchunks(chunk_bits, chunks):
    out_bytes = []
    next_read_chunk = 0
    next_read_bit = 0
    byte = 0
    bits_left = 8

    while next_read_chunk < len(chunks):
        can_fill = chunk_bits - next_read_bit
        to_fill = min(bits_left, can_fill)
        offset = chunk_bits - next_read_bit - to_fill

        byte <<= to_fill
        shifted = chunks[next_read_chunk] & (((1 << to_fill) - 1) << offset)
        byte |= shifted >> offset
        bits_left -= to_fill
        next_read_bit += to_fill

        if bits_left <= 0:
            out_bytes.append(byte)
            byte = 0
            bits_left = 8

        if next_read_bit >= chunk_bits:
            next_read_chunk += 1
            next_read_bit -= chunk_bits

    return out_bytes


def extract_packet(freqs):
    freqs = freqs[::2]
    bit_chunks = [int(round((f - START_HZ) / STEP_HZ)) for f in freqs]
    bit_chunks = [c for c in bit_chunks if 0 <= c < (2 ** BITS)]
    return bytearray(decode_bitchunks(BITS, bit_chunks))


def display(s):
    cprint(figlet_format(s.replace(' ', '   '), font='doom'), 'yellow')


def listen_windows(frame_rate=44100, interval=0.1):
    in_packet = False
    packet = []

    def callback(indata, frames, time, status):
        nonlocal in_packet, packet
        if status:
            print(status, file=sys.stderr)
        chunk = indata[:, 0] 
        chunk = np.array(chunk * 32767, dtype=np.int16)
        dom = dominant(frame_rate, chunk)

        if in_packet and match(dom, HANDSHAKE_END_HZ):
            byte_stream = extract_packet(packet)
            try:
                decoded_tuple = RSCodec(FEC_BYTES).decode(byte_stream)
                message_bytes = decoded_tuple[0]
                try:
                    text = message_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text = repr(message_bytes)
                display(text)
                display("")
            except ReedSolomonError as e:
                print("{}: {}".format(e, byte_stream))
            packet = []
            in_packet = False
        elif in_packet:
            packet.append(dom)
        elif match(dom, HANDSHAKE_START_HZ):
            in_packet = True

    with sd.InputStream(channels=1,
                        samplerate=frame_rate,
                        dtype='float32',
                        callback=callback,
                        blocksize=int(frame_rate * interval / 2)):
        print("Listening... Press Ctrl+C to stop.")
        while True:
            sd.sleep(1000)


if __name__ == '__main__':
    colorama.init(strip=not sys.stdout.isatty())
    listen_windows()
