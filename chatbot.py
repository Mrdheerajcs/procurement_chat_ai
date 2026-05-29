from fastapi import FastAPI, Query, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import base64
from fastapi.responses import FileResponse
from pathlib import Path
import multiprocessing
import logging
from Models.offline_chatbot import ChatbotProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Initialize FastAPI app
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Procurement Chatbot API",
    description="Hybrid PDF + Database Query Chatbot for Procurement"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB_URL = "postgresql://mmudevdb:mmudevdb@103.133.215.182/Procurement"

# ─────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    use_database: Optional[bool] = True
    
class ChatResponse(BaseModel):
    response: str
    source: str
    error: bool
    has_pdf: Optional[bool] = None
    has_database: Optional[bool] = None

# ─────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────

@app.post("/chat/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and append a PDF document for the chatbot knowledge base."""
    try:
        save_dir = ChatbotProcessor.DEFAULT_PDF_DIRECTORY
        os.makedirs(save_dir, exist_ok=True)

        file_path = os.path.join(save_dir, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Append the new PDF to the existing chatbot database
        processor = ChatbotProcessor.get_instance()
        success = processor.process_pdf(file_path)

        if success:
            return {
                "message": "Document added successfully and integrated into chatbot knowledge base.",
                "file": file.filename,
                "path": file_path
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to process document")
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """
    Send a message to the hybrid chatbot.
    
    - Queries PDF documents
    - Queries procurement database
    - Returns combined results from both sources
    """
    try:
        processor = ChatbotProcessor.get_instance()
        response = processor.chat(request.message, use_database=request.use_database)
        
        return {
            "response": response.get("response", ""),
            "source": response.get("source", "hybrid"),
            "error": response.get("error", False),
            "has_pdf": response.get("has_pdf"),
            "has_database": response.get("has_database")
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/clear")
async def clear_chat():
    """Clear the chat history."""
    try:
        processor = ChatbotProcessor.get_instance()
        processor.clear_history()
        return {"message": "Chat history cleared"}
    except Exception as e:
        logger.error(f"Clear history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/history")
async def get_chat_history():
    """Get the list of PDF questions in the knowledge base."""
    try:
        processor = ChatbotProcessor.get_instance()
        history = processor.get_chat_history()
        return {
            "history": history,
            "count": len(history),
            "source": "pdf_knowledge_base"
        }
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/status")
async def get_chatbot_status():
    """Get the status and capabilities of the chatbot."""
    try:
        processor = ChatbotProcessor.get_instance()
        pdf_count = len(processor.stored_questions)
        
        return {
            "status": "online",
            "version": "2.0",
            "capabilities": {
                "pdf_qa": True,
                "database_queries": True,
                "hybrid_mode": True
            },
            "knowledge_base": {
                "pdf_documents": len([f for f in os.listdir(ChatbotProcessor.DEFAULT_PDF_DIRECTORY) if f.endswith('.pdf')]) if os.path.exists(ChatbotProcessor.DEFAULT_PDF_DIRECTORY) else 0,
                "pdf_questions": pdf_count
            },
            "database": {
                "tables": 9,
                # "url": "postgresql://***@103.133.215.182/Procurement"
            }
        }
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Welcome endpoint."""
    return {
        "message": "Procurement Chatbot API",
        # "version": "2.0",
        "documentation": "/docs"
    }


def start_api_server():
    """Start the FastAPI server."""
    uvicorn.run(
        "chatbot:app",
        host="0.0.0.0",
        port=8950,
        reload=True
    )

if __name__ == "__main__":
    multiprocessing.freeze_support()
    start_api_server()
