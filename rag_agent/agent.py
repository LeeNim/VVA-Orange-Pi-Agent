import asyncio
import logging
import subprocess
import os
import time
from stt_manager import STTManager
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CẤU HÌNH ---
# Sử dụng os.path.expanduser để Python hiểu đúng đường dẫn ~
PIPER_EXE = os.path.expanduser("~/rkllama/piper/piper/piper")
PIPER_MODEL = "./vi_VN-25hours_single-low.onnx"
MEMORY_FILE = "chat_history.md"
VECTOR_STORE_PATH = "vector_store/"
LLM_API_BASE = "http://127.0.0.1:8080/v1"

async def speak(text):
    """Phát âm thanh Piper với Timeout để tránh treo hệ thống."""
    if not text: return
    try:
        clean_text = text.replace("*", "").replace("#", "").replace("-", " ")
        cmd = (f'echo "{clean_text}" | {PIPER_EXE} --model {PIPER_MODEL} --output_raw | '
               f'aplay -r 22050 -f S16_LE -t raw -c 1')
        
        process = await asyncio.create_subprocess_shell(cmd)
        try:
            # Nếu sau 15 giây AI vẫn chưa nói xong (hoặc treo do ko có loa), tự ngắt
            await asyncio.wait_for(process.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            logger.warning("TTS quá lâu, tự động ngắt để tiếp tục.")
            process.kill()
    except Exception as e:
        logger.error(f"Lỗi TTS: {e}")

def save_memory(u, a):
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"**User ({time.strftime('%H:%M:%S')}):** {u}\n")
        f.write(f"**AI:** {a}\n\n")

def get_history(n=2):
    if not os.path.exists(MEMORY_FILE): return ""
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip().split("\n\n")
            return "\n".join(content[-n:])
    except Exception: return ""

def setup_rag_chain():
    print("Đang khởi tạo RAG Chain...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
    
    template = """Bạn là trợ lý ảo tiếng Việt. Hãy trả lời dựa trên ngữ cảnh và lịch sử sau.
    Ngữ cảnh: {context}
    Câu hỏi và lịch sử: {question}
    Trợ lý:"""
    
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    llm = ChatOpenAI(base_url=LLM_API_BASE, api_key="EMPTY", model="qwen2.5-ins:0.5b")

    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=db.as_retriever(search_kwargs={"k": 3}),
        input_key="question",
        chain_type_kwargs={"prompt": prompt}
    )

async def main():
    qa_chain = setup_rag_chain()
    stt = STTManager()
    print("\n[AGENT] Sẵn sàng! Hãy bắt đầu nói...")
    
    try:
        # Vòng lặp generator của STT Manager
        async for user_text in stt.start_listening():
            print(f"\nUser: {user_text}")
            
            # CHUYỂN TRẠNG THÁI BẬN: Tạm ngưng STT nhưng không đóng vòng lặp
            stt.is_busy = True 
            
            history = get_history()
            merged_input = f"Lịch sử hội thoại:\n{history}\n\nCâu hỏi mới: {user_text}"
            
            try:
                print("Agent đang suy nghĩ...")
                response = await asyncio.to_thread(
                    qa_chain.invoke, {"question": merged_input}
                )
                answer = response['result']
                print(f"Agent: {answer}")
                
                save_memory(user_text, answer)
                
                # Chờ phát âm thanh xong mới quay lại nghe tiếp
                await speak(answer)
                
            except Exception as e:
                logger.error(f"Lỗi: {e}")
            finally:
                # Dọn dẹp hàng đợi để loại bỏ tiếng loa/nhiễu và mở lại mic
                stt.flush_queue()
                stt.is_busy = False
                print("\n[Đã sẵn sàng nghe tiếp...]")
                
    except KeyboardInterrupt:
        print("\nExit.")
        stt.running = False

if __name__ == "__main__":
    asyncio.run(main())