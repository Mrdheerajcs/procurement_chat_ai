"""
Database Integration Module for Procurement Chatbot
Provides semantic table routing and dynamic query generation
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from sentence_transformers import SentenceTransformer, util
import torch
from Models.sql_connection.connection import execute_sql_query
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# TABLE METADATA & SEMANTIC DESCRIPTIONS
# ─────────────────────────────────────────────────────────────

TABLE_METADATA = {
    "mpr_header": {
        "description": "Material Purchase Request header containing MPR details, approval status, priority, project info, dates, and total values",
        "purpose": "Track MPR creation, status, approvals, and delivery schedules",
        "key_columns": ["mpr_id", "mpr_no", "mpr_date", "status", "approval_status", "total_value", "priority", "department_id"],
        "keywords": ["mpr", "purchase request", "approval", "status", "priority", "project"],
        "business_domain": "MPR Management"
    },
    "mpr_details": {
        "description": "Line items in an MPR containing item codes, descriptions, quantities, rates, GST, and estimates",
        "purpose": "Store individual item details for each MPR including consumption, rates, and pricing",
        "key_columns": ["mpr_detail_id", "mpr_id", "item_code", "item_name", "requested_qty", "estimated_rate", "estimated_value", "gst_percent"],
        "keywords": ["items", "quantity", "rate", "item code", "consumption", "specification"],
        "business_domain": "MPR Items"
    },
    "tender_header": {
        "description": "Tender master containing tender information, bid dates, evaluation criteria, and tender status",
        "purpose": "Manage tender creation, publication, and tender lifecycle tracking",
        "key_columns": ["tender_id", "tender_no", "tender_date", "status", "closing_date", "bid_opening_date"],
        "keywords": ["tender", "bid", "rfq", "closing date", "evaluation"],
        "business_domain": "Tender Management"
    },
    "contract": {
        "description": "Contract records containing awarded vendor information, contract amounts, dates, and status",
        "purpose": "Track contracts awarded after tender closure, vendor selection, and contract lifecycle",
        "key_columns": ["contract_id", "contract_no", "tender_id", "vendor_id", "vendor_name", "amount", "start_date", "end_date", "status"],
        "keywords": ["contract", "vendor", "award", "amount", "dates", "status"],
        "business_domain": "Contract Management"
    },
    "bid_financial": {
        "description": "Financial bid information containing encrypted bid amounts, GST, bank details, EMD, and BOQ data",
        "purpose": "Store vendor's financial bid data with encryption and EMD information",
        "key_columns": ["bid_financial_id", "tender_id", "vendor_id", "encrypted_total_bid_amount", "encrypted_gst_percent", "emd_value", "submitted_at"],
        "keywords": ["bid", "financial", "amount", "gst", "emd", "bank", "boq"],
        "business_domain": "Bid Management"
    },
    "bid_technical": {
        "description": "Technical bid containing vendor credentials, certifications, experience, turnover, and evaluation status",
        "purpose": "Track technical qualifications, evaluations, and compliance verification of vendors",
        "key_columns": ["bid_technical_id", "tender_id", "vendor_id", "company_name", "bidder_turnover", "evaluation_status", "evaluation_score"],
        "keywords": ["technical", "evaluation", "qualification", "turnover", "certification", "experience"],
        "business_domain": "Bid Evaluation"
    },
    "audit_log": {
        "description": "Complete audit trail of all system actions including user activities, changes, and timestamps",
        "purpose": "Track and log all user actions and data modifications for compliance and auditing",
        "key_columns": ["id", "action", "entity_type", "entity_id", "username", "timestamp", "old_value", "new_value"],
        "keywords": ["audit", "log", "action", "user", "change", "history", "timestamp"],
        "business_domain": "Audit Trail"
    },
    "offline_bid_registration": {
        "description": "Offline/physical bid submission records containing envelope info, storage location, opening details",
        "purpose": "Manage physical bid submissions and opening procedures for offline tenders",
        "key_columns": ["offline_bid_id", "tender_id", "vendor_id", "vendor_name", "receipt_number", "status", "submission_timestamp"],
        "keywords": ["offline bid", "physical", "envelope", "receipt", "opening", "storage"],
        "business_domain": "Offline Bidding"
    },
    "mas_vendor": {
        "description": "Master vendor database containing vendor details, contact info, bank details, certifications, and blacklist status",
        "purpose": "Maintain vendor master data including credentials, compliance status, and contact information",
        "key_columns": ["vendor_id", "vendor_code", "vendor_name", "gst_no", "pan_no", "status", "is_blacklisted", "contact_person"],
        "keywords": ["vendor", "supplier", "contractor", "details", "credentials", "blacklist"],
        "business_domain": "Vendor Management"
    }
}

# ─────────────────────────────────────────────────────────────
# QUERY TEMPLATES FOR COMMON PATTERNS
# ─────────────────────────────────────────────────────────────

QUERY_TEMPLATES = {
    "count": "SELECT COUNT(*) as count FROM {table}",
    "status_distribution": "SELECT status, COUNT(*) as count FROM {table} GROUP BY status",
    "recent_records": "SELECT * FROM {table} ORDER BY {date_column} DESC LIMIT {limit}",
    "summary": "SELECT * FROM {table} LIMIT {limit}",
    "by_status": "SELECT * FROM {table} WHERE status = '{status}' LIMIT {limit}",
    "by_date_range": "SELECT * FROM {table} WHERE {date_column} BETWEEN '{start_date}' AND '{end_date}' LIMIT {limit}",
}

class DatabaseQueryGenerator:
    """Generates SQL queries based on semantic understanding of questions"""
    
    def __init__(self, model: SentenceTransformer):
        self.model = model
        self.table_embeddings = {}
        self.table_names = list(TABLE_METADATA.keys())
        self._init_table_embeddings()

    @staticmethod
    def _has_any(text: str, keywords: List[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _is_count_question(question: str) -> bool:
        return any(keyword in question for keyword in ["how many", "total", "count", "number of"])

    @staticmethod
    def _escape_sql_literal(value: str) -> str:
        return value.replace("'", "''")

    @staticmethod
    def _availability_mark(value) -> str:
        if value is None:
            return "❌"
        if isinstance(value, str) and not value.strip():
            return "❌"
        return "✅"

    @staticmethod
    def _extract_vendor_lookup(question: str) -> Optional[str]:
        patterns = [
            r"\bvendor\s+details\s+(?:of\s+|for\s+)?(.+)$",
            r"\bvendor\s+info(?:rmation)?\s+(?:of\s+|for\s+)?(.+)$",
            r"\bdetails\s+(?:of\s+|for\s+)?vendor\s+(.+)$",
            r"\bshow\s+(?:me\s+)?vendor\s+(.+)$",
            r"\bfind\s+vendor\s+(.+)$",
            r"\bsearch\s+vendor\s+(.+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, question, flags=re.IGNORECASE)
            if match:
                vendor_name = match.group(1).strip(" .,:;()[]{}\"'")
                if vendor_name and vendor_name.lower() not in ["details", "info", "information", "list", "master", "data"]:
                    return vendor_name
        return None
    
    def _init_table_embeddings(self):
        """Create semantic embeddings for each table"""
        for table_name, metadata in TABLE_METADATA.items():
            # Combine description, keywords, and purpose for rich embedding
            text = f"{metadata['description']} {' '.join(metadata['keywords'])} {metadata['purpose']}"
            embedding = self.model.encode(text, convert_to_tensor=True)
            self.table_embeddings[table_name] = embedding
            
    def find_relevant_tables(self, question: str, threshold: float = 0.4) -> List[Tuple[str, float]]:
        """
        Find which table(s) are most relevant to the question using semantic similarity
        Returns list of (table_name, similarity_score) tuples
        """
        question_embedding = self.model.encode(question, convert_to_tensor=True)
        
        scores = []
        for table_name, table_embedding in self.table_embeddings.items():
            similarity = util.cos_sim(question_embedding, table_embedding).item()
            if similarity > threshold:
                scores.append((table_name, similarity))
        
        # Sort by similarity descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Question: {question}")
        logger.info(f"Relevant tables: {scores}")
        
        return scores
    
    def generate_query(self, table_name: str, question: str, limit: int = 10) -> Optional[str]:
        """
        Generate a SQL query based on the question and table
        This is a heuristic-based approach; can be enhanced with ML later
        """
        question_lower = question.lower()
        metadata = TABLE_METADATA.get(table_name)
        
        if not metadata:
            return None
        
        is_count_query = self._is_count_question(question_lower)

        # Filter-specific queries should run before generic status/count handling.
        if table_name == "mas_vendor":
            select_cols = "vendor_name, vendor_code, gst_no, contact_person, status, is_blacklisted"
            detail_cols = (
                "vendor_name, vendor_code, email_id, gst_no, address_line1, address_line2, city, country, "
                "pan_document_path, drug_license_no, gst_document_path, com_certificate_path, other_documents_path"
            )
            active_filter = (
                "UPPER(COALESCE(status::text, '')) IN ('Y', 'YES', 'ACTIVE', 'APPROVED', '1', 'TRUE') "
                "AND UPPER(COALESCE(is_blacklisted::text, 'N')) NOT IN ('Y', 'YES', 'TRUE', '1')"
            )
            inactive_filter = "UPPER(COALESCE(status::text, '')) IN ('N', 'NO', 'INACTIVE', 'DEACTIVATED', '0', 'FALSE')"
            blacklisted_filter = "UPPER(COALESCE(is_blacklisted::text, 'N')) IN ('Y', 'YES', 'TRUE', '1')"
            vendor_lookup = self._extract_vendor_lookup(question)

            if vendor_lookup:
                lookup = self._escape_sql_literal(vendor_lookup)
                return (
                    f"SELECT {detail_cols} FROM {table_name} "
                    f"WHERE vendor_name ILIKE '%{lookup}%' OR vendor_code ILIKE '%{lookup}%' "
                    f"ORDER BY vendor_name LIMIT {limit}"
                )

            if self._has_any(question_lower, ["blacklist", "blacklisted"]):
                if is_count_query:
                    return f"SELECT COUNT(*) as total_count FROM {table_name} WHERE {blacklisted_filter}"
                return f"SELECT {select_cols} FROM {table_name} WHERE {blacklisted_filter} LIMIT {limit}"

            if self._has_any(question_lower, ["inactive", "deactivated", "disabled"]):
                if is_count_query:
                    return f"SELECT COUNT(*) as total_count FROM {table_name} WHERE {inactive_filter}"
                return f"SELECT {select_cols} FROM {table_name} WHERE {inactive_filter} LIMIT {limit}"

            if self._has_any(question_lower, ["active", "registered", "approved vendor"]):
                if is_count_query:
                    return f"SELECT COUNT(*) as total_count FROM {table_name} WHERE {active_filter}"
                return f"SELECT {select_cols} FROM {table_name} WHERE {active_filter} LIMIT {limit}"

            if self._has_any(question_lower, ["vendor", "supplier", "contractor"]):
                if is_count_query:
                    return f"SELECT COUNT(*) as total_count FROM {table_name}"
                return f"SELECT {select_cols} FROM {table_name} LIMIT {limit}"

        if table_name == "bid_technical":
            select_cols = "company_name, vendor_id, tender_id, evaluation_status, evaluation_score, evaluated_at"
            qualified_filter = "UPPER(COALESCE(evaluation_status::text, '')) IN ('QUALIFIED', 'PASSED', 'PASS', 'APPROVED', 'ACCEPTED')"
            pending_filter = "UPPER(COALESCE(evaluation_status::text, '')) IN ('PENDING', 'UNDER EVALUATION', 'UNDER_EVALUATION', 'IN PROGRESS', 'IN_PROGRESS')"
            rejected_filter = "UPPER(COALESCE(evaluation_status::text, '')) IN ('REJECTED', 'FAILED', 'FAIL', 'DISQUALIFIED', 'NOT QUALIFIED')"

            if self._has_any(question_lower, ["rejected", "failed", "disqualified", "not qualified"]):
                if is_count_query:
                    return f"SELECT COUNT(*) as total_count FROM {table_name} WHERE {rejected_filter}"
                return f"SELECT {select_cols} FROM {table_name} WHERE {rejected_filter} LIMIT {limit}"

            if self._has_any(question_lower, ["pending", "under evaluation", "in progress"]):
                if is_count_query:
                    return f"SELECT COUNT(*) as total_count FROM {table_name} WHERE {pending_filter}"
                return f"SELECT {select_cols} FROM {table_name} WHERE {pending_filter} LIMIT {limit}"

            if self._has_any(question_lower, ["qualified", "qualification", "passed", "pass bids", "eligible"]):
                if is_count_query:
                    return f"SELECT COUNT(*) as total_count FROM {table_name} WHERE {qualified_filter}"
                return f"SELECT {select_cols} FROM {table_name} WHERE {qualified_filter} LIMIT {limit}"

            if self._has_any(question_lower, ["evaluation", "score", "technical", "bid"]):
                if is_count_query:
                    return f"SELECT COUNT(*) as total_count FROM {table_name}"
                return f"SELECT {select_cols} FROM {table_name} LIMIT {limit}"

        if table_name == "mpr_header":
            approved_filter = "UPPER(COALESCE(approval_status::text, '')) = 'APPROVED'"
            pending_filter = "UPPER(COALESCE(approval_status::text, '')) = 'PENDING'"
            rejected_filter = "UPPER(COALESCE(approval_status::text, '')) = 'REJECTED'"
            high_priority_filter = "UPPER(COALESCE(priority::text, '')) = 'HIGH'"

            if self._has_any(question_lower, ["approved"]):
                if is_count_query:
                    return f"SELECT COUNT(*) as total_count FROM {table_name} WHERE {approved_filter}"
                return f"SELECT mpr_no, approval_status, total_value, priority, status FROM {table_name} WHERE {approved_filter} LIMIT {limit}"

            if self._has_any(question_lower, ["pending"]):
                if is_count_query:
                    return f"SELECT COUNT(*) as total_count FROM {table_name} WHERE {pending_filter}"
                return f"SELECT mpr_no, approval_status, total_value, priority, status FROM {table_name} WHERE {pending_filter} LIMIT {limit}"

            if self._has_any(question_lower, ["rejected"]):
                if is_count_query:
                    return f"SELECT COUNT(*) as total_count FROM {table_name} WHERE {rejected_filter}"
                return f"SELECT mpr_no, approval_status, total_value, priority, status FROM {table_name} WHERE {rejected_filter} LIMIT {limit}"

            if self._has_any(question_lower, ["high priority", "urgent"]):
                if is_count_query:
                    return f"SELECT COUNT(*) as total_count FROM {table_name} WHERE {high_priority_filter}"
                return f"SELECT mpr_no, priority, total_value, status, approval_status FROM {table_name} WHERE {high_priority_filter} LIMIT {limit}"

        # Pattern matching for common query types
        
        # Count queries: "how many", "total", "count"
        if is_count_query:
            return f"SELECT COUNT(*) as total_count FROM {table_name}"
        
        # Status-related queries
        if "status" in question_lower and table_name == "mpr_header":
            return f"SELECT mpr_no, status, approval_status, created_at FROM {table_name} ORDER BY created_at DESC LIMIT {limit}"
        
        if "status" in question_lower:
            status_col = "status" if "status" in [col.split()[-1] for col in metadata['key_columns']] else metadata['key_columns'][0]
            return f"SELECT status, COUNT(*) as count FROM {table_name} GROUP BY status"
        
        # Recent/latest queries: "recent", "latest", "last"
        if any(keyword in question_lower for keyword in ["recent", "latest", "last", "new"]):
            date_cols = [col for col in metadata['key_columns'] if 'date' in col or 'at' in col]
            if date_cols:
                date_col = date_cols[0]
                return f"SELECT * FROM {table_name} ORDER BY {date_col} DESC LIMIT {limit}"
        
        # MPR-related
        if table_name == "mpr_header":
            if "priority" in question_lower:
                return f"SELECT mpr_no, priority, total_value, status FROM {table_name} ORDER BY created_at DESC LIMIT {limit}"
            if "approval" in question_lower:
                return f"SELECT mpr_no, approval_status, approved_by_level1, approved_by_level2 FROM {table_name} LIMIT {limit}"
        
        # Contract-related
        if table_name == "contract":
            if "vendor" in question_lower or "winner" in question_lower or "award" in question_lower:
                return f"SELECT contract_no, vendor_name, amount, award_date, status FROM {table_name} LIMIT {limit}"
        
        # Default: select key columns
        select_cols = ", ".join(metadata['key_columns'][:6])  # Select first 6 key columns
        return f"SELECT {select_cols} FROM {table_name} LIMIT {limit}"
    
    def answer_question(self, question: str, db_url: str) -> Dict:
        """
        Main method: Answer a question by finding relevant table and generating query
        Only queries the most relevant table(s) when confidence is high
        """
        try:
            # Find relevant tables
            relevant_tables = self.find_relevant_tables(question, threshold=0.35)
            
            if not relevant_tables:
                return {
                    "response": "I couldn't find relevant data for your question. Please try rephrasing.",
                    "source": "database",
                    "error": True
                }
            
            results = []
            top_similarity = relevant_tables[0][1] if relevant_tables else 0
            vendor_lookup = self._extract_vendor_lookup(question)
            
            # Only query tables with high confidence match
            # If best match is high (>0.65), only query the top 1
            # If moderate (0.45-0.65), query top 2
            # If lower, query top 3
            if vendor_lookup:
                tables_to_query = [("mas_vendor", 1.0)]
            elif top_similarity > 0.65:
                tables_to_query = relevant_tables[:1]
            elif top_similarity > 0.50:
                tables_to_query = relevant_tables[:2]
            else:
                tables_to_query = relevant_tables[:3]
            
            logger.info(f"Question: {question}")
            logger.info(f"Top similarity: {top_similarity:.3f} - Querying {len(tables_to_query)} table(s)")
            
            # Query only the selected tables
            for table_name, similarity in tables_to_query:
                try:
                    query = self.generate_query(table_name, question, limit=10)
                    if query:
                        logger.info(f"Executing query on {table_name}: {query}")
                        df = execute_sql_query(query, db_url)
                        
                        if not df.empty:
                            results.append({
                                "table": table_name,
                                "similarity": round(similarity, 3),
                                "data": df.to_dict('records'),
                                "row_count": len(df)
                            })
                except Exception as e:
                    logger.error(f"Error querying {table_name}: {e}")
                    continue
            
            if not results:
                return {
                    "response": "Query executed but returned no results. Please try a different question.",
                    "source": "database",
                    "error": True
                }
            
            # Format response
            response_text = self._format_response(question, results)
            
            return {
                "response": response_text,
                "source": "database",
                "results": results,
                "error": False
            }
            
        except Exception as e:
            logger.error(f"Error in answer_question: {e}")
            return {
                "response": f"An error occurred: {str(e)}",
                "source": "database",
                "error": True
            }
    
    def _format_response(self, question: str, results: List[Dict]) -> str:
        """Format database results into intelligent, conversational responses"""
        if not results:
            return "No data found."

        if self._extract_vendor_lookup(question):
            vendor_result = next((result for result in results if result.get('table') == "mas_vendor"), None)
            if vendor_result:
                return self._format_vendor_response(
                    vendor_result.get('data', []),
                    vendor_result.get('row_count', 0),
                    question.lower()
                )
        
        # Analyze the data to generate insights
        insights = self._analyze_data(results, question)
        return insights


    def _analyze_data(self, results: List[Dict], question: str) -> str:
        """Analyze query results and generate intelligent, conversational response"""
        
        question_lower = question.lower()
        response_text = "## Procurement System Summary\n"
        response_text += "I analyzed the procurement database and found information related to your query.\n\n"
        
        sections = []
        
        for result in results:
            table = result['table']
            data = result['data']
            row_count = result['row_count']
            
            if not data:
                continue
            
            # Generate insights based on table type and question
            if table == "mas_vendor":
                sections.append(self._format_vendor_response(data, row_count, question_lower))
            
            elif table == "contract":
                sections.append(self._format_contract_response(data, row_count, question_lower))
            
            elif table == "bid_technical":
                sections.append(self._format_bid_technical_response(data, row_count, question_lower))
            
            elif table == "bid_financial":
                sections.append(self._format_bid_financial_response(data, row_count, question_lower))
            
            elif table == "mpr_header":
                sections.append(self._format_mpr_response(data, row_count, question_lower))
            
            elif table == "mpr_details":
                sections.append(self._format_mpr_details_response(data, row_count, question_lower))
            
            elif table == "offline_bid_registration":
                sections.append(self._format_offline_bid_response(data, row_count, question_lower))
            
            else:
                sections.append(self._format_generic_response(table, data, row_count))
        
        response_text += "\n\n".join(sections)
        return response_text
    
    # ─────────────────────────────────────────────────────────
    # Response Formatters for Each Table
    # ─────────────────────────────────────────────────────────
    
    def _format_vendor_response(self, data: List[Dict], row_count: int, question: str) -> str:
        """Generate simple vendor list response"""
        lines = []
        lines.append("### Vendors")
        lines.append("")

        if data and "total_count" in data[0]:
            label = "vendors"
            if "inactive" in question or "deactivated" in question:
                label = "inactive vendors"
            elif "blacklist" in question:
                label = "blacklisted vendors"
            elif "active" in question:
                label = "active vendors"
            lines.append(f"I found {data[0].get('total_count', 0)} {label}.")
            return "\n".join(lines)

        if data and any(key in data[0] for key in ["email_id", "address_line1", "address_line2", "city", "country"]):
            for record in data:
                vendor_name = record.get('vendor_name') or 'N/A'
                vendor_code = record.get('vendor_code') or 'N/A'
                email_id = record.get('email_id') or 'N/A'
                gst_no = record.get('gst_no') or 'N/A'
                address_parts = [
                    record.get('address_line1'),
                    record.get('address_line2'),
                    record.get('city'),
                    record.get('country'),
                ]
                address = ", ".join(str(part).strip() for part in address_parts if part and str(part).strip()) or 'N/A'

                lines.append(f"Name - {vendor_name} ({vendor_code})")
                lines.append(f"E-mail - {email_id}")
                lines.append(f"GST No - {gst_no}")
                lines.append(f"Address - {address}")
                lines.append("")
                lines.append("Uploaded Docs")
                lines.append(f"Pan No - {self._availability_mark(record.get('pan_document_path'))}")
                lines.append(f"Company License - {self._availability_mark(record.get('drug_license_no'))}")
                lines.append(f"Company Gst No - {self._availability_mark(record.get('gst_document_path'))}")
                lines.append(f"Company certificate - {self._availability_mark(record.get('com_certificate_path'))}")
                lines.append(f"Other docs - {self._availability_mark(record.get('other_documents_path'))}")
                lines.append("")

            return "\n".join(lines).rstrip()
        
        vendors_seen = set()
        for record in data:
            vendor_name = record.get('vendor_name', 'N/A')
            vendor_code = record.get('vendor_code', 'N/A')
            gst_no = record.get('gst_no', '')
            status = record.get('status', '')
            is_blacklisted = record.get('is_blacklisted', 'N')
            
            # Avoid duplicates
            if vendor_name not in vendors_seen and vendor_name != 'N/A':
                vendors_seen.add(vendor_name)
                status_value = str(status).strip().upper() if status is not None else ''
                blacklist_value = str(is_blacklisted).strip().upper() if is_blacklisted is not None else ''
                status_text = "Active" if status_value in ["Y", "YES", "ACTIVE", "APPROVED", "1", "TRUE"] else "Inactive"
                blacklist_text = " (Blacklisted)" if blacklist_value in ["Y", "YES", "TRUE", "1"] else ""
                lines.append(f"- {vendor_name} ({vendor_code}) | Status: {status_text}{blacklist_text}")
        
        return "\n".join(lines)
    
    def _format_contract_response(self, data: List[Dict], row_count: int, question: str) -> str:
        """Generate markdown-formatted contract analysis response"""
        lines = []
        
        lines.append("### Contract Overview")
        
        total_value = 0
        awarded_count = 0
        signed_count = 0
        pending_count = 0
        vendors_involved = set()
        highest_contract = None
        highest_amount = 0
        
        contract_details = []
        
        for record in data:
            contract_no = record.get('contract_no', 'N/A')
            vendor_name = record.get('vendor_name', 'N/A')
            amount = record.get('amount', 0)
            status = record.get('status', 'N/A')
            
            vendors_involved.add(vendor_name)
            
            if amount:
                try:
                    amount_float = float(amount)
                    total_value += amount_float
                    if amount_float > highest_amount:
                        highest_amount = amount_float
                        highest_contract = f"{vendor_name} worth ₹{amount_float:,.0f}"
                except (ValueError, TypeError):
                    pass
            
            # Safe status comparison
            status_str = str(status).strip().upper() if status is not None else ''
            if status_str == 'AWARDED':
                awarded_count += 1
            elif status_str == 'SIGNED':
                signed_count += 1
            else:
                pending_count += 1
            
            contract_details.append((contract_no, vendor_name, amount, status))
        
        lines.append(f"The system currently contains {row_count} contract(s) with a combined value of ₹{total_value:,.0f}.")
        lines.append("")
        
        lines.append("Contract Status")
        lines.append("")
        lines.append(f"- Awarded Contracts: {awarded_count}")
        lines.append(f"- Signed Contracts: {signed_count}")
        if pending_count > 0:
            lines.append(f"- Pending Contracts: {pending_count}")
        lines.append("")
        
        if highest_contract:
            lines.append("Highest Value Contract")
            lines.append("")
            lines.append(f"- {highest_contract}")
        
        return "\n".join(lines)
    
    def _format_bid_technical_response(self, data: List[Dict], row_count: int, question: str) -> str:
        """Generate simple technical bid list response"""
        lines = []
        lines.append("### Technical Bids")
        lines.append("")

        if data and "total_count" in data[0]:
            label = "technical bids"
            if "not qualified" in question or "rejected" in question or "failed" in question or "disqualified" in question:
                label = "rejected technical bids"
            elif "pending" in question:
                label = "pending technical bids"
            elif "qualified" in question or "passed" in question:
                label = "qualified technical bids"
            lines.append(f"I found {data[0].get('total_count', 0)} {label}.")
            return "\n".join(lines)
        
        companies_seen = set()
        for record in data:
            company = record.get('company_name', 'N/A')
            status = record.get('evaluation_status', 'N/A')
            score = record.get('evaluation_score', 'N/A')
            
            # Avoid duplicates
            if company not in companies_seen and company != 'N/A':
                companies_seen.add(company)
                lines.append(f"- {company} | Status: {status} | Score: {score}")
        
        return "\n".join(lines)
    
    def _format_bid_financial_response(self, data: List[Dict], row_count: int, question: str) -> str:
        """Generate simple financial bid list response"""
        lines = []
        lines.append("### Financial Bids")
        lines.append("")
        
        vendors_seen = set()
        for record in data:
            vendor_id = record.get('vendor_id', 'N/A')
            tender_id = record.get('tender_id', 'N/A')
            emd_value = record.get('emd_value', 'N/A')
            submitted_at = record.get('submitted_at', 'N/A')
            
            # Avoid duplicates by vendor_id
            if vendor_id not in vendors_seen and vendor_id != 'N/A':
                vendors_seen.add(vendor_id)
                lines.append(f"- Vendor {vendor_id} | Tender: {tender_id} | EMD: {emd_value}")
        
        return "\n".join(lines)
    
    def _format_mpr_response(self, data: List[Dict], row_count: int, question: str) -> str:
        """Generate markdown-formatted MPR analysis response"""
        lines = []
        
        lines.append("Material Purchase Requests")

        if data and "total_count" in data[0]:
            label = "MPR(s)"
            if "approved" in question:
                label = "approved MPR(s)"
            elif "pending" in question:
                label = "pending MPR(s)"
            elif "rejected" in question:
                label = "rejected MPR(s)"
            elif "high priority" in question or "urgent" in question:
                label = "high-priority MPR(s)"
            lines.append(f"I found {data[0].get('total_count', 0)} {label}.")
            return "\n".join(lines)
        
        pending = 0
        approved = 0
        rejected = 0
        total_value = 0
        high_priority_count = 0
        
        for record in data:
            status = record.get('approval_status', 'PENDING')
            priority = record.get('priority', 'NORMAL')
            value = record.get('total_value', 0)
            
            if value:
                try:
                    total_value += float(value)
                except (ValueError, TypeError):
                    pass
            
            # Safe status comparison
            status_str = str(status).strip().upper() if status is not None else ''
            if status_str == 'APPROVED':
                approved += 1
            elif status_str == 'REJECTED':
                rejected += 1
            else:
                pending += 1
            
            # Safe priority comparison
            priority_str = str(priority).strip().upper() if priority is not None else ''
            if priority_str == 'HIGH':
                high_priority_count += 1
        
        lines.append(f"I found {row_count} MPR(s) in the system with a combined value of ₹{total_value:,.0f}.")
        lines.append("")
        
        lines.append("Approval Status Distribution")
        lines.append("")
        lines.append(f"- Approved: {approved}")
        lines.append(f"- Pending: {pending}")
        if rejected > 0:
            lines.append(f"- Rejected: {rejected}")
        lines.append("")
        
        if high_priority_count > 0:
            lines.append("Priority Alert")
            lines.append("")
            lines.append(f"- {high_priority_count} MPR(s) marked as HIGH priority requiring immediate attention.")
        
        return "\n".join(lines)
    
    def _format_mpr_details_response(self, data: List[Dict], row_count: int, question: str) -> str:
        """Generate markdown-formatted MPR items analysis response"""
        lines = []
        
        lines.append("MPR Line Items")
        
        total_value = 0
        high_value_items = []
        
        for record in data:
            item_name = record.get('item_name', 'N/A')
            est_value = record.get('estimated_value', 0)
            
            if est_value:
                try:
                    val_float = float(est_value)
                    total_value += val_float
                    high_value_items.append((item_name, val_float))
                except (ValueError, TypeError):
                    pass
        
        lines.append(f"I found {row_count} item(s) in the MPR with a total estimated value of ₹{total_value:,.0f}.")
        lines.append("")
        
        # Sort and show top items
        high_value_items.sort(key=lambda x: x[1], reverse=True)
        if high_value_items:
            lines.append("#### Top Items by Value")
            lines.append("")
            for item_name, value in high_value_items[:5]:
                lines.append(f"- {item_name}: ₹{value:,.0f}")
        
        return "\n".join(lines)
    
    def _format_offline_bid_response(self, data: List[Dict], row_count: int, question: str) -> str:
        """Generate markdown-formatted offline bid analysis response"""
        lines = []
        
        lines.append("### Offline Bid Submissions")
        
        opened_count = 0
        sealed_count = 0
        pending_count = 0
        
        for record in data:
            status = record.get('status', 'N/A')
            # Safe status comparison
            status_str = str(status).strip().upper() if status is not None else ''
            if status_str == 'OPENED':
                opened_count += 1
            elif status_str == 'SEALED':
                sealed_count += 1
            else:
                pending_count += 1
        
        lines.append(f"I found {row_count} offline bid submission(s) in the system.")
        lines.append("")
        
        lines.append("Submission Status")
        lines.append("")
        lines.append(f"- Opened: {opened_count}")
        lines.append(f"- Sealed: {sealed_count}")
        if pending_count > 0:
            lines.append(f"- Pending Processing: {pending_count}")
        
        return "\n".join(lines)
    
    def _format_generic_response(self, table: str, data: List[Dict], row_count: int) -> str:
        """Generate markdown-formatted generic response for unknown table types"""
        lines = []
        lines.append(f"{table.replace('_', ' ').title()} Information")
        lines.append("")
        lines.append(f"I found {row_count} record(s) in the {table.replace('_', ' ')} table.")
        lines.append("")
        
        lines.append("#### Summary")
        lines.append("")
        for i, record in enumerate(data[:3], 1):
            items = []
            for key, value in list(record.items())[:3]:
                items.append(f"{key}: {value}")
            lines.append(f"{i}. {' | '.join(items)}")
        
        if row_count > 3:
            lines.append(f"\n... and {row_count - 3} more record(s)")
        
        return "\n".join(lines)
