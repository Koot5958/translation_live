# App parameters
MAX_LEN = 10
REFRESH_RATE_FAST = 0.1
REFRESH_RATE_SLOW = 0.3
REFRESH_TRANSLATE_RATE = 0.1

# Default languages
DEFAULT_AUDIO_LANG = "French (France)"
DEFAULT_TRANS_LANG = "English (United States)"

# Thread names
THREAD_NAMES = ["speech_to_text", "translate"]

# Display
LOG_TITLE = "[Logs]"

# Audio stream
SR = 16000
CHUNK = int(SR / 10)