#!/usr/bin/env python3
"""
Test script for hybrid chatbot (PDF + Database)
"""

import sys
import os
sys.path.insert(0, '/Users/rozaltheric/Office Work/procurement_chat_ai')

from Models.offline_chatbot import ChatbotProcessor
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_chatbot():
    """Test the hybrid chatbot with sample questions"""
    
    print("\n" + "="*70)
    print("HYBRID CHATBOT TEST (PDF + DATABASE)")
    print("="*70 + "\n")
    
    try:
        # Initialize chatbot
        print("📦 Initializing chatbot...")
        processor = ChatbotProcessor.get_instance()
        print("✅ Chatbot initialized successfully!\n")
        
        # Test questions
        test_questions = [
            "hello",
            "how many MPRs are there?",
            "show me recent tenders",
            "what are the contract amounts?",
            "list all vendors",
            "which vendors are blacklisted?",
            "what is the MPR approval status?",
            "show me bid information",
            "what is the latest procurement activity?",
        ]
        
        print("Testing with sample questions:\n")
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n{'─'*70}")
            print(f"Question {i}: {question}")
            print('─'*70)
            
            response = processor.chat(question, use_database=True)
            
            print(f"\n📋 Response:")
            print(f"   Source: {response.get('source', 'N/A')}")
            print(f"   Has PDF: {response.get('has_pdf', False)}")
            print(f"   Has Database: {response.get('has_database', False)}")
            print(f"   Error: {response.get('error', False)}")
            print(f"\n📝 Answer:\n{response.get('response', 'No response')}")
        
        print("\n" + "="*70)
        print("✅ Test completed successfully!")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False
    
    return True

if __name__ == "__main__":
    success = test_chatbot()
    sys.exit(0 if success else 1)
