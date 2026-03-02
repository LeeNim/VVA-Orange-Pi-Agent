# 🇻🇳 VVA — Vietnamese Voice Assistant

> Trợ lý giọng nói tiếng Việt chạy hoàn toàn cục bộ (offline) trên thiết bị nhỏ.

---

## 📌 Tổng quan — Vision dự án

**VVA (Vietnamese Voice Assistant)** là dự án mã nguồn mở nhằm tạo ra một trợ lý AI giọng nói tiếng Việt có thể:

- 🔒 **Chạy hoàn toàn cục bộ** — Không gửi bất kỳ dữ liệu nào ra bên ngoài. Người dùng hoàn toàn làm chủ dữ liệu và AI của mình.
- 🗣️ **Hỗ trợ tiếng Việt** — Từ nhận diện giọng nói (STT), xử lý ngôn ngữ (LLM), đến phát giọng nói (TTS) đều hỗ trợ tiếng Việt.
- 📦 **Chạy trên thiết bị nhỏ** — Được thiết kế để hoạt động trên các SBC (Single Board Computer) như Orange Pi, Raspberry Pi, v.v.
- 🧠 **RAG Agent** — Tích hợp hệ thống truy xuất tài liệu (Retrieval-Augmented Generation) với FAISS, cho phép AI trả lời dựa trên dữ liệu riêng của người dùng.

---

## 🛠️ Thư viện & Công cụ sử dụng

### LLM Server — `rkllama`
| Thành phần | Chi tiết |
|---|---|
| **Server** | [rkllama](./rkllama/) — Server LLM cục bộ với API tương thích OpenAI |
| **Model** | `qwen2.5-ins:0.5b` (hoặc model tùy chọn trong `rkllama/models/`) |
| **API Endpoint** | `http://127.0.0.1:8080/v1` |

### Speech-to-Text (STT) — Nhận diện giọng nói
| Thành phần | Chi tiết |
|---|---|
| **Whisper Model** | [PhoWhisper-small-ct2](https://huggingface.co/Niem/PhoWhisper-small-ct2) — Model Whisper tối ưu cho tiếng Việt |
| **VAD** | [Silero VAD](https://github.com/snakers4/silero-vad) (ONNX) — Phát hiện giọng nói để biết khi nào người dùng bắt đầu/ngừng nói |
| **Runtime** | `faster-whisper` với CTranslate2 (int8, CPU) |
| **Audio** | `sounddevice` + ALSA driver |

### Text-to-Speech (TTS) — Phát giọng nói
| Thành phần | Chi tiết |
|---|---|
| **Engine** | [Piper TTS](./piper/) — TTS offline, nhẹ, tốc độ cao |
| **Voice Model** | `vi_VN-25hours_single-low.onnx` — Giọng nói tiếng Việt |
| **Output** | `aplay` qua ALSA (22050Hz, S16_LE, mono) |

### RAG (Retrieval-Augmented Generation)
| Thành phần | Chi tiết |
|---|---|
| **Framework** | LangChain |
| **Vector Store** | FAISS (CPU) — Truy xuất vector nhanh chóng |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Data** | Tài liệu `.txt` trong thư mục `rag_agent/data/` |

### Các thư viện Python chính
```
langchain, langchain-community, langchain-openai, langchain-huggingface
faiss-cpu, sentence-transformers
faster-whisper, silero-vad
sounddevice, numpy, torch
websockets, piper-tts
```

---

## 📁 Cấu trúc dự án

```
rkllama/
├── rkllama/              # Server LLM cục bộ (API tương thích OpenAI)
│   └── models/           # Kho chứa các model LLM
├── piper/                # Piper TTS engine (phát giọng nói offline)
├── livekit/              # WhisperLiveKit server (STT qua WebSocket)
│   └── venv/             # Virtual environment chứa dependencies
├── rag_agent/            # 🧠 Agent chính
│   ├── agent.py          # Vòng lặp chính: nghe → suy nghĩ → trả lời → nói
│   ├── stt_manager.py    # Quản lý STT cục bộ (Silero VAD + PhoWhisper)
│   ├── whisper_client.py # Client WebSocket kết nối WhisperLiveKit server
│   ├── ingest.py         # Nạp tài liệu vào FAISS vector store
│   ├── data/             # Thư mục chứa tài liệu cho RAG
│   ├── vector_store/     # FAISS index (tự động tạo sau khi chạy ingest.py)
│   ├── chat_history.md   # Lịch sử hội thoại (tự động lưu)
│   └── requirements.txt  # Dependencies
├── venv/                 # Virtual environment của rkllama
└── README.md             # File này
```

---

## ✅ Dự án đã làm được gì

- [x] **LLM Server cục bộ** — rkllama server hoạt động với API tương thích OpenAI
- [x] **Speech-to-Text cục bộ** — PhoWhisper + Silero VAD, nhận diện giọng nói tiếng Việt trực tiếp từ mic
- [x] **Text-to-Speech cục bộ** — Piper TTS phát giọng nói tiếng Việt
- [x] **RAG Agent** — Truy xuất tài liệu qua FAISS và trả lời dựa trên ngữ cảnh
- [x] **Vòng lặp hội thoại hoàn chỉnh** — Nghe mic → VAD phát hiện giọng nói → STT → RAG + LLM → TTS → Phát loa
- [x] **Lịch sử hội thoại** — Lưu và sử dụng lịch sử chat để trả lời có ngữ cảnh
- [x] **Chống nhiễu** — Tạm ngưng mic khi AI đang nói để tránh thu tiếng loa

---

## ⚠️ Hạn chế hiện tại

- **Tốc độ xử lý** — Chạy trên CPU nên tốc độ suy luận LLM và STT còn chậm, đặc biệt trên SBC
- **Chất lượng giọng nói TTS** — Model Piper tiếng Việt hiện tại (`low`) chất lượng chưa cao
- **Embeddings chưa tối ưu cho tiếng Việt** — Đang dùng `all-MiniLM-L6-v2` (model đa ngôn ngữ), chưa có model embedding chuyên tiếng Việt
- **Chưa có wake word** — Chưa có từ khóa đánh thức (ví dụ: "Hey VVA"), hiện tại mic luôn nghe
- **Driver âm thanh** — Phụ thuộc ALSA driver cụ thể cho từng board (hiện cấu hình cho rockchip-es8388)
- **Chưa hỗ trợ định dạng tài liệu đa dạng** — Hiện chỉ hỗ trợ file `.txt` cho RAG ingestion
- **Chưa có giao diện** — Chỉ hoạt động qua terminal

---

## �️ Roadmap

### Phase 1 — Ổn định & Nâng cao phần mềm cốt lõi
> *Ưu tiên cao nhất — nền tảng vững chắc trước khi mở rộng.*

- [ ] **Wake word detection** — Thêm từ khóa đánh thức (ví dụ: "Hey VVA") để tiết kiệm tài nguyên, mic không cần nghe liên tục
- [ ] **Hỗ trợ nhiều định dạng tài liệu** — PDF, DOCX, Markdown, v.v. cho RAG ingestion
- [ ] **Model embedding tiếng Việt** — Thay `all-MiniLM-L6-v2` bằng model embedding chuyên biệt tiếng Việt để cải thiện độ chính xác truy xuất
- [ ] **Nâng cấp TTS** — Sử dụng model giọng nói tiếng Việt chất lượng cao hơn (medium/high)
- [ ] **Multi-turn conversation** — Cải thiện quản lý ngữ cảnh hội thoại dài, tóm tắt lịch sử thông minh hơn

---

### Phase 2 — Giao diện Web Dashboard
> *Biến VVA từ dự án terminal thành sản phẩm người dùng có thể tương tác dễ dàng.*

- [ ] **Hotspot mode** — Nếu chưa kết nối WiFi, VVA tự phát WiFi (AP mode) để người dùng vào dashboard cấu hình qua trình duyệt
- [ ] **Kết nối WiFi** — Chọn WiFi, nhập mật khẩu và kết nối ngay từ dashboard. Sau khi kết nối, người dùng truy cập dashboard qua IP
- [ ] **Quản lý LLM** — Thay đổi bộ não AI:
  - Tải model từ Hugging Face (đã quantize sẵn) về chạy cục bộ
  - Hoặc kết nối tới model trả phí (OpenAI, Gemini, v.v.) chỉ cần nhập API key
- [ ] **Quản lý TTS** — Thay đổi giọng nói của Agent theo ý muốn (chọn voice model khác)
- [ ] **Giao diện nhắn tin** — Chat với Agent bằng text nếu không muốn dùng giọng nói
- [ ] **Quản lý hội thoại** — Lựa chọn đoạn chat cũ để tiếp tục, hoặc tạo đoạn chat mới
- [ ] **Tùy chỉnh khuôn mặt Agent** — Thay đổi hình ảnh/biểu cảm hiển thị trên màn hình (nếu có phần cứng hỗ trợ)

---

### Phase 3 — Plugin System & MCP
> *Mở rộng khả năng của Agent ra thế giới bên ngoài — nhưng vẫn do người dùng kiểm soát.*

- [ ] **Plugin system (Tools)** — Agent có thể hiểu và sử dụng các tool tự tạo (điều khiển IoT, tra cứu thời tiết, hẹn giờ, v.v.)
- [ ] **MCP Server** — Kết nối tới MCP (Model Context Protocol) server để cung cấp thêm công cụ cho Agent khi có mạng:
  - Gmail, Google Drive, Spotify, Calendar, Search, v.v.
  - Thêm/xóa/chỉnh sửa link MCP server từ dashboard
  - Tải và chạy Docker MCP server ngay trên thiết bị
  - Tùy từng MCP mà cần hoặc không cần API key — config từ dashboard
- [ ] **USB Auto-Scan** — Khi cắm USB:
  1. Tự động quét virus
  2. Đọc các file hỗ trợ (txt, pdf, docx, v.v.)
  3. Tự nạp nội dung vào kiến thức (FAISS vector store) của Agent
  4. Hiển thị tiến trình trên màn hình

---

### Phase 4 — Nâng cấp phần cứng
> *Từ prototype sang thiết bị thực tế.*

- [ ] **SBC mạnh hơn** — Chuyển sang board có RAM lớn hơn (16GB+) để chạy model lớn hơn, CPU khỏe hơn để suy luận nhanh hơn
- [ ] **Giao thức I2S** — Sử dụng I2S cho mic array và DAC/amplifier chuyên dụng, cải thiện chất lượng thu/phát âm thanh
- [ ] **Màn hình hiển thị** — Thêm màn hình để:
  - Hiển thị biểu cảm khuôn mặt của Agent (vui, suy nghĩ, đang nghe, v.v.)
  - Biểu thị thông tin cần thiết (trạng thái, tiến trình, kết quả, v.v.)
  - Hiển thị tiến trình USB scan, tải model, v.v.
- [ ] **Tối ưu hiệu năng** — Tận dụng NPU (nếu SBC hỗ trợ) cho suy luận AI nhanh hơn
- [ ] **Nguồn điện di động** — Tích hợp pin sạc hoặc mạch năng lượng mặt trời (solar panel) để thiết bị có thể hoạt động độc lập, không cần cắm điện liên tục

---

### Phase 5 — Mở rộng khả năng
> *VVA không chỉ là trợ lý giọng nói — mà còn là công cụ hỗ trợ công việc.*

- [ ] **Code Assistant** — Host model code đã tối ưu trên thiết bị, kết nối với máy tính qua mạng LAN/WiFi để hỗ trợ lập trình (autocomplete, giải thích code, debug, v.v.)
- [ ] **Agentic workflow** — Agent tự lập kế hoạch và thực thi chuỗi hành động phức tạp
- [ ] **Multi-language** — Hỗ trợ thêm ngôn ngữ khác ngoài tiếng Việt
- [ ] **OTA Update** — Cập nhật phần mềm từ xa qua mạng

---

### Phase 6 — Cộng đồng & Hệ sinh thái
> *Xây dựng cộng đồng xung quanh VVA — càng nhiều người dùng, càng nhiều lựa chọn.*

- [ ] **VVA Model Hub** — Liên tục tối ưu, fine-tune và đăng tải các model lên Hugging Face để người dùng có thể tải về sử dụng ngay:
  - Model LLM đã quantize cho SBC (GGUF, ONNX, v.v.)
  - Model STT tiếng Việt fine-tuned
  - Model TTS giọng Việt chất lượng cao
  - Model embedding tiếng Việt chuyên biệt
- [ ] **Cộng đồng đóng góp** — Xây dựng cộng đồng người dùng và nhà phát triển, chia sẻ plugin, MCP server, voice model, và cấu hình thiết bị
- [ ] **Thiết kế vỏ máy** — Thiết kế 3D case đẹp, sẵn sàng in 3D hoặc đặt gia công, cho trải nghiệm sản phẩm hoàn chỉnh
- [ ] **Tài liệu hướng dẫn** — Wiki, video hướng dẫn lắp ráp, cài đặt và sử dụng chi tiết cho người mới

---

## 🚀 Cách sử dụng hiện tại

### Yêu cầu
- Board ARM64 (Orange Pi, Raspberry Pi, v.v.) hoặc máy tính Linux
- Mic + Loa kết nối qua ALSA
- Python 3.10+

### Bước 1: Khởi động LLM Server

Sử dụng venv của `~/rkllama`:

```bash
# Terminal 1 — Khởi động rkllama server
source ~/rkllama/venv/bin/activate
rkllama_server --models ~/rkllama/rkllama/models/
```

```bash
# Terminal 2 — Load model LLM
source ~/rkllama/venv/bin/activate
rkllama_client load <tên_model>
# Ví dụ: rkllama_client load qwen2.5-ins:0.5b

# Xem thêm các lệnh có sẵn:
rkllama_client --help
```

### Bước 2: (Tùy chọn) Nạp tài liệu cho RAG

```bash
# Đặt file .txt vào thư mục data/
cp tai_lieu_cua_ban.txt ~/rkllama/rag_agent/data/

# Chạy ingestion
source ~/rkllama/livekit/venv/bin/activate
cd ~/rkllama/rag_agent
python3.10 ingest.py
```

### Bước 3: Chạy Agent

Sử dụng venv trong `livekit` (chứa các thư viện cần thiết):

```bash
source ~/rkllama/livekit/venv/bin/activate
cd ~/rkllama/rag_agent
python3.10 agent.py
```

Agent sẽ:
1. Khởi tạo RAG Chain (FAISS + LLM)
2. Bật mic và bắt đầu nghe
3. Khi phát hiện giọng nói → dịch sang text → truy xuất tài liệu → gửi tới LLM → phát giọng trả lời

---

## 📝 Ghi chú

- Cấu hình audio device ID (`DEVICE_ID`) trong `stt_manager.py` và `whisper_client.py` có thể khác nhau tùy thiết bị. Dùng `arecord -l` để xem danh sách thiết bị âm thanh.
- Model LLM có thể thay đổi bằng cách sửa biến `model` trong `agent.py`.
- Lịch sử hội thoại được lưu tại `rag_agent/chat_history.md`.

---

## 📄 License

Xem [LICENSE](./rkllama/LICENSE) của rkllama.
