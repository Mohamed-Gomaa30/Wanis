import re

def normalize_arabic_text(text):
    """
    Comprehensive Arabic text normalization for consistent evaluation
    
    Args:
        text (str): Input Arabic text
        
    Returns:
        str: Normalized Arabic text
    """
    if not text or not isinstance(text, str):
        return ""
    
    punctuation = r'[!\"#$%&\'()*+,-./:;<=>?@[\\\\]^_`{|}~،؛؟]'
    text = re.sub(punctuation, '', text)

    diacritics = r'[\u064B-\u0652]'
    text = re.sub(diacritics, '', text)
    
    text = re.sub('پ', 'ب', text)
    text = re.sub('ڤ', 'ف', text)
    text = re.sub(r'[آ]', 'ا', text)
    text = re.sub(r'[أإ]', 'ا', text)
    text = re.sub(r'[ؤ]', 'و', text)
    text = re.sub(r'[ئ]', 'ي', text)
    text = re.sub(r'[ء]', '', text)

    eastern_to_western_numerals = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', 
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }
    for eastern, western in eastern_to_western_numerals.items():
        text = text.replace(eastern, western)

    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def preprocess_audio(audio_array, sampling_rate, target_sampling_rate=16000):
    """
    Basic audio preprocessing for Whisper models
    
    Args:
        audio_array (np.array): Input audio array
        sampling_rate (int): Original sampling rate
        target_sampling_rate (int): Target sampling rate (default 16kHz for Whisper)
        
    Returns:
        np.array: Processed audio array
    """
    import numpy as np
    
    if sampling_rate != target_sampling_rate:
        from scipy import signal
        audio_array = signal.resample(
            audio_array, 
            int(len(audio_array) * target_sampling_rate / sampling_rate)
        )
    
    if audio_array.dtype != np.float32:
        audio_array = audio_array.astype(np.float32) / np.iinfo(audio_array.dtype).max
    
    return audio_array