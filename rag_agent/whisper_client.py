import asyncio
import websockets
import json
import logging
import numpy as np
import sounddevice as sd
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CẤU HÌNH ---
SERVER_URL = "ws://127.0.0.1:8000/asr"
SAMPLE_RATE = 16000
CHANNELS = 2         # Giữ 2 kênh cho driver rockchip-es8388
DEVICE_ID = 2        # ID card âm thanh
BLOCK_SIZE = 2048
VAD_THRESHOLD = 500  # Ngưỡng âm lượng, điều chỉnh tùy mic
SILENCE_TIMEOUT = 1.5 # Thời gian chờ để chốt câu (giây)

class WhisperClient:
    def __init__(self, url=SERVER_URL):
        self.url = url
        self.running = False
        self.queue = None
        self.loop = None
        self.is_speaking = False
        self.silence_start_time = 0

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio status: {status}")
        
        # 1. Trích xuất kênh trái (mic native)
        left_channel = indata[:, 0].copy()
        
        # 2. Tính năng lượng âm thanh (RMS)
        rms = np.sqrt(np.mean(left_channel.astype(np.float32)**2))
        
        # 3. Logic VAD gửi dữ liệu
        if rms > VAD_THRESHOLD:
            if not self.is_speaking:
                logger.info("VAD: Đang nói...")
                self.is_speaking = True
            self.silence_start_time = 0
            # Gửi dữ liệu an toàn từ thread của sounddevice sang asyncio loop
            self.loop.call_soon_threadsafe(self.queue.put_nowait, left_channel.tobytes())
        else:
            if self.is_speaking:
                if self.silence_start_time == 0:
                    self.silence_start_time = time.time()
                
                # Vẫn gửi thêm một đoạn im lặng ngắn để server chốt chữ cuối
                if time.time() - self.silence_start_time < SILENCE_TIMEOUT:
                    self.loop.call_soon_threadsafe(self.queue.put_nowait, left_channel.tobytes())
                else:
                    logger.info("VAD: Im lặng (Ngừng gửi)")
                    self.is_speaking = False
                    self.silence_start_time = 0

    async def stream_audio(self, websocket):
        while self.running:
            try:
                data = await self.queue.get()
                await websocket.send(data)
            except Exception as e:
                logger.error(f"Error sending audio: {e}")
                break

    async def receive_transcription(self, websocket):
        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get("type") == "config": continue
                
                # Ưu tiên lấy text từ buffer (đang nối dần)
                text = data.get("buffer_transcription", "").strip()
                
                # Nếu có lines (kết quả đã chốt), lấy dòng cuối cùng
                if "lines" in data and len(data["lines"]) > 0:
                    text = data["lines"][-1].get("text", "").strip()

                if text:
                    yield text
            except Exception:
                continue

    async def start(self):
        self.running = True
        self.loop = asyncio.get_running_loop()
        self.queue = asyncio.Queue()
        
        try:
            async with websockets.connect(self.url) as websocket:
                logger.info(f"Kết nối thành công tới {self.url}")
                with sd.InputStream(device=DEVICE_ID, samplerate=SAMPLE_RATE,
                                    channels=CHANNELS, dtype='int16',
                                    blocksize=BLOCK_SIZE, callback=self.audio_callback):
                    
                    sender_task = asyncio.create_task(self.stream_audio(websocket))
                    async for text in self.receive_transcription(websocket):
                        yield text
                    await sender_task
        except Exception as e:
            logger.error(f"Lỗi kết nối: {e}")
        finally:
            self.running = False