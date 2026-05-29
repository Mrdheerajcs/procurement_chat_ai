import os
import pdfplumber
import time
import threading
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from sentence_transformers import SentenceTransformer, util
import torch
import sys
import logging
from Models.database_integration import DatabaseQueryGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Path where the model is saved locally after the first download.
# Change this to any folder you prefer.
# ─────────────────────────────────────────────────────────────

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)  # next to exe, NOT _internal
    return os.path.dirname(os.path.abspath(__file__))

LOCAL_MODEL_DIR = os.path.join(get_base_path(), "dependency", "all-MiniLM-L6-v2")
SBERT_MODEL_NAME = "all-MiniLM-L6-v2"

def load_sbert_model() -> SentenceTransformer:
    """
    Load SBERT model from local disk.
    If not present yet, download it ONCE and save it so future
    starts are fully offline.
    """
    # Check if model files exist (look for model weights)
    model_files = ['model.safetensors', 'pytorch_model.bin']
    has_model = False
    
    if os.path.isdir(LOCAL_MODEL_DIR):
        dir_contents = os.listdir(LOCAL_MODEL_DIR)
        has_model = any(f in dir_contents for f in model_files)
    
    if has_model:
        # ── Offline path: load from local folder ──
        print(f"[SBERT] Loading model from local cache: {LOCAL_MODEL_DIR}")
        return SentenceTransformer(LOCAL_MODEL_DIR)
    else:
        # ── First-time only: download and save ──
        print(
            f"[SBERT] Model not found locally. Downloading '{SBERT_MODEL_NAME}' "
            f"(requires internet — one-time only)..."
        )
        os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)
        model = SentenceTransformer(SBERT_MODEL_NAME)
        model.save(LOCAL_MODEL_DIR)
        print(f"[SBERT] Model saved to '{LOCAL_MODEL_DIR}'. Future starts are fully offline. ✓")
        return model


class PDFHandler(FileSystemEventHandler):
    """Handles real-time PDF processing when new files are added to the directory."""

    def __init__(self, chatbot_processor):
        self.chatbot_processor = chatbot_processor

    def on_created(self, event):
        if event.src_path.endswith(".pdf"):
            print(f"New PDF detected: {event.src_path}")

            # Wait until file is fully written
            time.sleep(2)

            # Retry mechanism
            for _ in range(5):
                try:
                    if os.path.exists(event.src_path):
                        success = self.chatbot_processor.process_pdf(event.src_path)
                        if success:
                            print(f"Processed: {event.src_path}")
                        return
                except Exception:
                    time.sleep(1)

            print(f"Failed to process PDF after retries: {event.src_path}")


class ChatbotProcessor:
    """Handles PDF processing and Database Q&A retrieval for procurement."""

    _instance = None
    DEFAULT_PDF_DIRECTORY = os.path.join(get_base_path(), "chatbot_qa")
    DB_URL = "postgresql://mmudevdb:mmudevdb@103.133.215.182/Procurement"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize chatbot processor with PDF and database capabilities."""
        # Load model from local cache — no internet after first run
        os.makedirs(self.DEFAULT_PDF_DIRECTORY, exist_ok=True)
        self.sbert_model = load_sbert_model()
        
        # PDF-related attributes
        self.question_embeddings = []
        self.stored_questions = []
        self.qa_pairs = {}
        self.pdf_content = ""
        
        # Database integration
        self.db_query_generator = DatabaseQueryGenerator(self.sbert_model)
        
        self.load_existing_pdfs()       # Load PDFs on startup
        self.start_folder_monitoring()  # Start monitoring in background
        
        logger.info("ChatbotProcessor initialized with PDF and Database capabilities")


    # ──────────────────────────────────────────────────────────
    # PDF handling
    # ──────────────────────────────────────────────────────────

    def load_existing_pdfs(self):
        """Loads PDFs from the defined directory."""
        if os.path.exists(self.DEFAULT_PDF_DIRECTORY):
            for filename in os.listdir(self.DEFAULT_PDF_DIRECTORY):
                if filename.endswith(".pdf"):
                    self.process_pdf(os.path.join(self.DEFAULT_PDF_DIRECTORY, filename))
        else:
            print(
                f"[PDF] Directory '{self.DEFAULT_PDF_DIRECTORY}' not found. "
                "Create it and add PDFs to enable document Q&A."
            )

    def get_embedding(self, text):
        return self.sbert_model.encode(text, convert_to_tensor=True)

    def process_pdf(self, file_path: str) -> bool:
        """Extracts questions and answers from a PDF and appends them to the database."""
        for attempt in range(5):
            try:    
                with pdfplumber.open(file_path) as pdf:
                    pdf_text = "\n".join(
                        page.extract_text() for page in pdf.pages if page.extract_text()
                    )

                lines = pdf_text.split("\n")
                current_question = None
                current_answer = []

                for line in lines:
                    stripped_line = line.strip()
                    if stripped_line.endswith("?"):
                        if current_question:
                            self.qa_pairs[current_question.lower()] = "\n".join(current_answer).strip()
                        current_question = stripped_line
                        current_answer = []
                        self.stored_questions.append(current_question)
                        embedding = self.get_embedding(current_question)
                        self.question_embeddings.append(embedding)
                        print(f"[DEBUG] Question: {current_question} | Embedding shape: {embedding.shape}")
                    elif current_question:
                        current_answer.append(stripped_line)

                if current_question:
                    self.qa_pairs[current_question.lower()] = "\n".join(current_answer).strip()

                return True
            except Exception as e:
                if attempt < 4:
                    print(f"[Retry {attempt+1}] File not ready, retrying...")
                    time.sleep(1)
                else:
                    print(f"Error processing PDF: {e}")
                    return False

    # ──────────────────────────────────────────────────────────
    # Matching
    # ──────────────────────────────────────────────────────────

    def find_best_match(self, user_input):
        if not self.question_embeddings:
            return None

        input_emb = self.get_embedding(user_input)
        question_tensor = torch.stack(self.question_embeddings)
        scores = util.cos_sim(input_emb, question_tensor)
        scores_flat = scores.squeeze(0)

        max_score, best_idx = torch.max(scores_flat, dim=0)
        max_score_value = max_score.item()

        print(f"[DEBUG] Max similarity score: {max_score_value:.4f}")
        if max_score_value > 0.75:
            return self.stored_questions[best_idx]
        return None

    # ──────────────────────────────────────────────────────────
    # Chat - Hybrid PDF + Database approach
    # ──────────────────────────────────────────────────────────

    def chat(self, message: str, use_database: bool = True) -> dict:
        """
        Matches user queries with PDF Q&A pairs and/or Database records.
        
        Args:
            message: User query
            use_database: Whether to include database results (default: True)
            
        Returns:
            dict with response, source, and metadata
        """
        try:
            # Handle greetings
            greetings = ["hi", "hello", "hey", "hola", "namaste"]
            well_being_questions = ["how are you", "how are you?", "how's it going", "how do you do"]

            if message.lower() in greetings:
                return {
                    "response": "Greetings! How can I assist you today? I can help with PDF documents or procurement database queries.",
                    "source": "greeting",
                    "error": False
                }

            if message.lower() in well_being_questions:
                return {
                    "response": "I am good and ready to help! I can search PDF documents or query the procurement database.",
                    "source": "greeting",
                    "error": False
                }

            responses = []
            
            # ─── Try PDF matching first ───
            pdf_result = self._try_pdf_match(message)
            if pdf_result and not pdf_result.get("error"):
                responses.append({
                    "type": "pdf",
                    "confidence": pdf_result.get("confidence", 0),
                    "response": pdf_result.get("response", "")
                })
            
            # ─── Try Database query ───
            if use_database:
                db_result = self._try_database_query(message)
                if db_result and not db_result.get("error"):
                    responses.append({
                        "type": "database",
                        "confidence": db_result.get("confidence", 0),
                        "response": db_result.get("response", ""),
                        "data": db_result.get("results", [])
                    })
            
            # ─── Return combined results ───
            if responses:
                combined_response = self._combine_responses(responses, message)
                return combined_response
            
            # If nothing found
            return {
                "response": "I couldn't find relevant information. Try asking about procurement processes, MPR status, vendor details, contracts, or bids.",
                "source": "hybrid",
                "error": True
            }
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return {
                "response": f"An error occurred: {str(e)}",
                "source": "hybrid",
                "error": True
            }

    def _try_pdf_match(self, user_input: str) -> dict:
        """Try to find answer in PDF Q&A pairs"""
        if not self.question_embeddings:
            return {"error": True, "response": None}
        
        try:
            input_emb = self.get_embedding(user_input)
            question_tensor = torch.stack(self.question_embeddings)
            scores = util.cos_sim(input_emb, question_tensor)
            scores_flat = scores.squeeze(0)

            max_score, best_idx = torch.max(scores_flat, dim=0)
            max_score_value = max_score.item()

            logger.info(f"PDF Match - Max similarity score: {max_score_value:.4f}")
            
            if max_score_value > 0.75:
                matched_question = self.stored_questions[best_idx]
                key = matched_question.lower().strip()
                answer = self.qa_pairs.get(key)
                
                if answer:
                    return {
                        "error": False,
                        "response": answer.replace("\n", " "),
                        "confidence": max_score_value,
                        "source": "pdf",
                        "matched_question": matched_question
                    }
                else:
                    return {
                        "error": True,
                        "response": "Matched PDF question but couldn't retrieve answer."
                    }
            
            return {"error": True}
            
        except Exception as e:
            logger.error(f"PDF matching error: {e}")
            return {"error": True}

    def _try_database_query(self, user_input: str) -> dict:
        """Try to find answer in database using intelligent query generation"""
        try:
            result = self.db_query_generator.answer_question(user_input, self.DB_URL)
            return result
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return {
                "response": f"Database query error: {str(e)}",
                "error": True
            }

    def _combine_responses(self, responses: list, question: str) -> dict:
        """Intelligently combine PDF and Database responses"""
        
        pdf_responses = [r for r in responses if r["type"] == "pdf"]
        db_responses = [r for r in responses if r["type"] == "database"]
        
        # Combine both sources
        combined_text = []
        
        if pdf_responses:
            for resp in pdf_responses:
                combined_text.append(f"{resp['response']}")
        
        if db_responses:
            for resp in db_responses:
                combined_text.append(f"{resp['response']}")
        
        final_response = "\n\n".join(combined_text) if combined_text else "No results found."
        
        return {
            "response": final_response,
            "source": "hybrid",
            "error": False,
            "has_pdf": len(pdf_responses) > 0,
            "has_database": len(db_responses) > 0,
            "details": responses
        }


    def get_chat_history(self):
        """Retrieves stored questions."""
        return self.stored_questions

    def clear_history(self):
        """Clear stored conversation history."""
        self.history = []

    def start_folder_monitoring(self):
        """Starts a background thread to monitor the directory for new PDFs."""
        if not os.path.exists(self.DEFAULT_PDF_DIRECTORY):
            os.makedirs(self.DEFAULT_PDF_DIRECTORY, exist_ok=True)

        event_handler = PDFHandler(self)

        if getattr(sys, 'frozen', False):
            observer = PollingObserver()
        else:
            observer = Observer()
            
        observer.schedule(event_handler, path=self.DEFAULT_PDF_DIRECTORY, recursive=False)
        observer_thread = threading.Thread(target=self._run_observer, args=(observer,), daemon=True)
        observer_thread.start()
        print(f"Monitoring '{self.DEFAULT_PDF_DIRECTORY}' for new PDFs in the background...")

    def _run_observer(self, observer):
        """Runs the observer loop in a background thread."""
        observer.start()
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()