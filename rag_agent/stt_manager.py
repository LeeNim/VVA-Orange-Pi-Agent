import torch
import numpy as np
import sounddevice as sd
import silero_vad
from faster_whisper import WhisperModel
import asyncio
import queue
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CẤU HÌNH ---
MODEL_PATH = "Niem/PhoWhisper-small-ct2"
VAD_THRESHOLD = 0.4
SILENCE_CHUNKS_LIMIT = 25 
SAMPLE_RATE = 16000
BLOCK_SIZE = 512 # Tăng lên một chút để ổn định hơn trên Orange Pi
DEVICE_ID = 2 

class STTManager:
    def __init__(self):
        logger.info("Đang tải model VAD và Whisper cục bộ...")
        self.vad_model = silero_vad.load_silero_vad(onnx=True)
        # Giới hạn thread để nhường tài nguyên cho hệ thống âm thanh
        self.whisper_model = WhisperModel(MODEL_PATH, device="cpu", compute_type="int8", cpu_threads=4)
        self.audio_queue = queue.Queue()
        self.running = False
        self.is_busy = False # Cờ hiệu trạng thái bận

    def audio_callback(self, indata, frames, time, status):
        if status: logger.warning(status)
        # Luôn cho dữ liệu vào queue, việc lọc sẽ xử lý ở vòng lặp chính
        self.audio_queue.put(indata[:, 0].copy())

    def flush_queue(self):
        """Xóa sạch dữ liệu âm thanh cũ trong hàng đợi"""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

    # Trong file stt_manager.py - Cập nhật hàm start_listening
    async def start_listening(self):
        self.running = True
        audio_buffer = []
        is_speaking = False
        silence_counter = 0

        stream = sd.InputStream(
            device=DEVICE_ID, samplerate=SAMPLE_RATE, 
            channels=2, dtype="float32", 
            blocksize=BLOCK_SIZE, callback=self.audio_callback
        )

        with stream:
            logger.info("STT Manager: Đang nghe...")
            while self.running:
                if self.is_busy:
                    # RESET TOÀN BỘ TRẠNG THÁI KHI BẬN
                    audio_buffer = []
                    is_speaking = False
                    silence_counter = 0
                    self.flush_queue() 
                    await asyncio.sleep(0.1)
                    continue

                try:
                    try:
                        chunk = self.audio_queue.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(0.01)
                        continue

                    chunk_tensor = torch.from_numpy(chunk)
                    speech_prob = self.vad_model(chunk_tensor, SAMPLE_RATE).item()

                    if speech_prob > VAD_THRESHOLD:
                        if not is_speaking:
                            is_speaking = True
                            audio_buffer = []
                            logger.info("[User bắt đầu nói...]")
                        audio_buffer.append(chunk)
                        silence_counter = 0
                    else:
                        if is_speaking:
                            silence_counter += 1
                            audio_buffer.append(chunk)
                            if silence_counter > SILENCE_CHUNKS_LIMIT:
                                is_speaking = False
                                logger.info("[Đang dịch...]")
                                full_audio = np.concatenate(audio_buffer)
                                
                                segments, _ = await asyncio.to_thread(
                                    self.whisper_model.transcribe, full_audio, beam_size=1
                                )
                                text = "".join(seg.text for seg in segments).strip()
                                
                                if text:
                                    yield text # Trả về text cho agent.py
                                
                                # Reset sau khi trả về kết quả
                                audio_buffer = []
                                silence_counter = 0
                                self.flush_queue()
                except Exception as e:
                    logger.error(f"Lỗi STT: {e}")