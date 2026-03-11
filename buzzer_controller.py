#!/usr/bin/env python3
"""
buzzer_controller.py - Advanced buzzer control
Uses PWM via RPi.GPIO by default for louder sound on 3.3V active buzzers.
Supports:
  - Morse code (letters and numbers)
  - Beep sequences (numbers separated by commas)
  - Volume control via PWM duty cycle (capped at 95%)
  - Speed control (WPM for morse)
  - Separate alert sounds for price high and price low
"""

import time
import logging

log = logging.getLogger(__name__)

MORSE = {
    'A': '.-',   'B': '-...', 'C': '-.-.', 'D': '-..',  'E': '.',
    'F': '..-.', 'G': '--.',  'H': '....', 'I': '..',   'J': '.---',
    'K': '-.-',  'L': '.-..', 'M': '--',   'N': '-.',   'O': '---',
    'P': '.--.', 'Q': '--.-', 'R': '.-.',  'S': '...',  'T': '-',
    'U': '..-',  'V': '...-', 'W': '.--',  'X': '-..-', 'Y': '-.--',
    'Z': '--..',
    '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
    '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
    '.': '.-.-.-', ',': '--..--', '?': '..--..', '!': '-.-.--',
    ' ': ' ',
}

def parse_input(text: str) -> dict:
    """Parse user input and return type (morse or sequence) with data."""
    text = text.strip().upper()
    if all(c in '0123456789, ' for c in text):
        parts = [p.strip() for p in text.replace(' ', ',').split(',') if p.strip()]
        try:
            nums = [int(p) for p in parts]
            return {"type": "sequence", "data": nums}
        except ValueError:
            pass
    return {"type": "morse", "data": text}

def morse_to_preview(text: str) -> str:
    """Convert text to morse visual representation."""
    result = []
    for char in text.upper():
        if char in MORSE:
            if char == ' ':
                result.append('   ')
            else:
                result.append(f"{char}: {MORSE[char]}")
        else:
            result.append(f"{char}: ?")
    return '  |  '.join(result)

def sequence_to_preview(nums: list) -> str:
    """Generate visual preview for beep sequences."""
    return '  ->  '.join([f'beep x{n}' for n in nums])

def get_preview(text: str) -> dict:
    """Return full preview dict for the web dashboard."""
    parsed = parse_input(text)
    if parsed["type"] == "morse":
        return {
            "type": "morse",
            "preview": morse_to_preview(parsed["data"]),
            "description": f"Morse: {parsed['data']}"
        }
    else:
        return {
            "type": "sequence",
            "preview": sequence_to_preview(parsed["data"]),
            "description": f"Sequence: {', '.join(str(n) for n in parsed['data'])} beeps"
        }


class BuzzerPlayer:
    """
    Controls buzzer via PWM (RPi.GPIO).
    Works well with 3.3V active buzzers — PWM increases effective volume.

    gpio   : BCM GPIO pin number
    volume : 0-100 (PWM duty cycle, capped at 95%)
    wpm    : morse speed in words per minute
    freq   : PWM frequency in Hz (2000 works well for active buzzers)
    """

    def __init__(self, gpio: int, volume: int = 80, wpm: int = 15, freq: int = 2000):
        self.gpio   = gpio
        self.volume = max(1, min(95, volume))  # capped at 95% — at 100% PWM becomes DC and buzzer stops vibrating
        self.wpm    = max(5, min(40, wpm))
        self.freq   = freq
        self._pwm   = None

    def _setup(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio, GPIO.OUT)
            self._pwm = GPIO.PWM(self.gpio, self.freq)
            self._pwm.start(0)
        except Exception as e:
            log.warning(f"Buzzer setup failed: {e}")
            raise

    def _cleanup(self):
        try:
            if self._pwm:
                self._pwm.stop()
            import RPi.GPIO as GPIO
            GPIO.cleanup(self.gpio)
        except Exception:
            pass
        self._pwm = None

    def _on(self):
        if self._pwm:
            self._pwm.ChangeDutyCycle(self.volume)

    def _off(self):
        if self._pwm:
            self._pwm.ChangeDutyCycle(0)

    def _beep(self, duration: float):
        self._on()
        time.sleep(duration)
        self._off()

    def _morse_unit(self) -> float:
        """Duration of one morse unit in seconds based on WPM."""
        return 1.2 / self.wpm

    def _play_morse_char(self, char: str):
        unit = self._morse_unit()
        code = MORSE.get(char.upper(), '')
        if char == ' ':
            time.sleep(unit * 7)
            return
        for symbol in code:
            if symbol == '.':
                self._beep(unit)
                time.sleep(unit)
            elif symbol == '-':
                self._beep(unit * 3)
                time.sleep(unit)
        time.sleep(unit * 2)

    def play_morse(self, text: str):
        """Play text as morse code."""
        try:
            self._setup()
            for char in text.upper():
                self._play_morse_char(char)
        except Exception as e:
            log.warning(f"Morse playback failed: {e}")
        finally:
            self._cleanup()

    def play_sequence(self, nums: list, beep_duration: float = 0.25,
                      pause_between: float = 0.15, pause_groups: float = 0.6):
        """
        Play a beep sequence.
        nums         : list of integers e.g. [1, 3, 2]
        beep_duration: duration of each beep in seconds
        pause_between: pause between beeps in the same group
        pause_groups : pause between different groups
        """
        try:
            self._setup()
            for i, count in enumerate(nums):
                for j in range(count):
                    self._beep(beep_duration)
                    if j < count - 1:
                        time.sleep(pause_between)
                if i < len(nums) - 1:
                    time.sleep(pause_groups)
        except Exception as e:
            log.warning(f"Sequence playback failed: {e}")
        finally:
            self._cleanup()

    def play(self, text: str):
        """Main interface — auto-detects morse or beep sequence."""
        parsed = parse_input(text)
        log.info(f"Buzzer play: {parsed}")
        if parsed["type"] == "morse":
            self.play_morse(parsed["data"])
        else:
            self.play_sequence(parsed["data"])


# ── Convenience functions ──────────────────────────────────────────────────────

def tocar_buzzer_padrao(gpio: int, vezes: int = 3, volume: int = 80):
    """Simple beeps for price alerts (legacy fallback)."""
    player = BuzzerPlayer(gpio=gpio, volume=volume)
    player.play_sequence([vezes])

def tocar_buzzer_custom(gpio: int, texto: str, volume: int = 80,
                        wpm: int = 15, use_pwm: bool = True):
    """Play custom input (morse or sequence)."""
    player = BuzzerPlayer(gpio=gpio, volume=volume, wpm=wpm)
    player.play(texto)

def tocar_alerta(gpio: int, pattern: str, volume: int = 80, wpm: int = 15):
    """
    Play a specific alert pattern.
    Falls back to 3 beeps if pattern is empty.
    """
    if pattern and pattern.strip():
        tocar_buzzer_custom(gpio=gpio, texto=pattern.strip(), volume=volume, wpm=wpm)
    else:
        tocar_buzzer_padrao(gpio=gpio, vezes=3, volume=volume)


if __name__ == "__main__":
    tests = ["SOS", "BITCOIN", "3", "1,2,3", "A"]
    for t in tests:
        p = get_preview(t)
        print(f"Input: '{t}' -> {p['description']}")
        print(f"  {p['preview']}\n")
