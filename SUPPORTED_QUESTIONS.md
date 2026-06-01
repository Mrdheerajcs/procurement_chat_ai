# 📋 Supported Questions List

Your chatbot now supports a wide variety of questions about the procurement system. Below is a comprehensive list organized by topic.

---

## ✅ **Vendor Management Questions**

Ask about vendors, suppliers, and vendor details:

| Question | Example |
|----------|---------|
| Vendor overview | "vendor details", "show vendors", "list all vendors" |
| Vendor status | "active vendors", "vendor status", "vendor list" |
| Vendor filters | "active vendors", "inactive vendors", "registered suppliers" |
| Vendor information | "vendor info", "vendor data", "supplier details" |
| Vendor lookup | "vendor details ABC Traders", "vendor info VEND001", "find vendor ABC" |
| Vendor uploaded docs | Included in vendor lookup results as available/not available indicators |
| Vendor blacklist | "blacklisted vendors", "vendor blacklist", "deactivated vendors" |
| Vendor search | "find vendors", "search vendors", "vendor master" |

**More variations:**
- "Who are the active vendors?"
- "How many active vendors are registered?"
- "Show inactive vendors"
- "Vendor details ABC Traders"
- "Find vendor VEND001"
- "Show me all registered vendors"
- "List the vendors in the system"
- "Vendor master data"
- "Supplier information"
- "Vendor contact details"

---

## 📦 **Contract & Award Questions**

Ask about contracts, agreements, and awards:

| Question | Example |
|----------|---------|
| Contract overview | "contracts", "show contracts", "list contracts" |
| Awarded contracts | "awarded contracts", "contract awards", "awarded vendors" |
| Contract status | "contract status", "signed contracts", "contract details" |
| Contract value | "contract amount", "contract value", "total contract value" |
| High-value contracts | "largest contracts", "highest value", "top contracts" |

**More variations:**
- "Show me all contracts"
- "What contracts are awarded?"
- "Contract information"
- "Purchase orders"
- "Agreement details"
- "Vendor contracts"

---

## 📄 **Tender Publication Questions**

Ask about tender publication details from `publish_tender_header`.
Responses return only tender number, tender name, tender description, and published date.

| Question | Example |
|----------|---------|
| Tender overview | "tender details", "show tenders", "list tenders" |
| Tender lookup | "tender details TEND001", "find tender Medicine Supply", "tender no TEND001" |
| Published tenders | "published tenders", "show published tender details" |
| Draft tenders | "draft tenders", "pending approval tenders" |
| Bid-open tenders | "bid open tenders", "show currently open tenders" |
| Awarded tenders | "awarded tenders", "show awarded tender details" |
| Closed tenders | "closed tenders", "expired tenders", "bid ended tenders" |

**More variations:**
- "Show me published tenders"
- "List tender details"
- "Tender details TEND001"
- "Find tender Medicine Supply"
- "Tender no TEND001"
- "Which tenders are open for bidding?"
- "Show closed tender details"
- "How many bid open tenders are there?"
- "How many published tenders are there?"

---

## 🎯 **Bid & Evaluation Questions**

Ask about bids, evaluations, and technical qualifications:

| Question | Example |
|----------|---------|
| Bid evaluation | "bid evaluation", "evaluate bids", "bid status" |
| Technical evaluation | "technical bids", "bid technical", "technical evaluation" |
| Qualified bids | "qualified bids", "pass bids", "qualified vendors" |
| Pending evaluation | "pending bids", "pending evaluation", "bids pending" |
| Rejected bids | "rejected bids", "failed bids", "disqualified vendors" |
| Bid statistics | "bid count", "number of bids", "bid statistics" |

**More variations:**
- "Show bid evaluations"
- "Which bids are qualified?"
- "How many qualified bids are there?"
- "Show pending technical bids"
- "List rejected technical bids"
- "Technical bid status"
- "Evaluation results"
- "Bid compliance"
- "Vendor qualification status"

---

## 💰 **Financial Questions**

Ask about financial bids, amounts, and money:

| Question | Example |
|----------|---------|
| Financial bids | "financial bids", "bid amount", "financial bid status" |
| Bid opening | "opened bids", "sealed bids", "bid opening status" |
| EMD & Bank | "emd", "earnest money", "bank details", "bid security" |
| Bid amounts | "bid values", "quoted amounts", "financial details" |

**More variations:**
- "Show financial bids"
- "Which bids are sealed?"
- "Opened bid envelope status"
- "Financial bid details"
- "Cost and pricing"

---

## 📮 **Purchase Request Questions**

Ask about MPRs (Material Purchase Requests):

| Question | Example |
|----------|---------|
| MPR status | "purchase requests", "mpr status", "mpr list" |
| Approved requests | "approved mpr", "approved requests", "approved purchase" |
| Pending requests | "pending mpr", "pending requests", "pending approval" |
| Rejected requests | "rejected mpr", "rejected requests", "declined purchase" |
| High priority | "high priority", "urgent requests", "priority mpr" |
| Request details | "mpr details", "request items", "line items" |

**More variations:**
- "Show purchase requests"
- "Material purchase status"
- "How many approved MPRs are there?"
- "Show rejected MPRs"
- "Pending approvals"
- "Request summary"
- "Procurement requests"
- "What MPRs are pending?"

---

## 📊 **Analytics & Summary Questions**

Ask for overviews and summaries:

| Question | Example |
|----------|---------|
| System overview | "procurement overview", "system summary", "data summary" |
| Total statistics | "total vendors", "total contracts", "total bids" |
| Status distribution | "contract status", "bid status distribution", "approval distribution" |
| Data quality | "data quality", "incomplete records", "missing data" |

**More variations:**
- "Give me a summary"
- "Show statistics"
- "Data overview"
- "System status"
- "Procurementmetrics"

---

## 🔄 **Offline & Physical Bids**

Ask about offline/physical bid submissions:

| Question | Example |
|----------|---------|
| Offline bids | "offline bids", "physical bids", "envelope bids" |
| Bid receipt | "receipt number", "offline submission", "physical submission" |
| Opening status | "offline opening", "physical bid status", "offline submission status" |

**More variations:**
- "Show offline bids"
- "Physical bid submissions"
- "Offline bid envelope status"
- "Physical submission records"

---

## 💡 **Pro Tips for Better Questions**

### ✅ What Works Well:
- Clear, specific terms: "vendor details", "contracts", "bid evaluation"
- Business context: "approved contracts", "qualified bids", "pending requests"
- Natural phrases: "show me", "list", "tell me", "give me"
- Data fields: "amount", "status", "date", "value"

### ❌ What Doesn't Work:
- Too vague: "data", "information", "stuff"
- SQL syntax: "SELECT * FROM contracts"
- Off-topic: "tell jokes", "weather", "news"

### 🎯 Best Practices:
1. **Be specific** - Use table names or field names when possible
2. **Use action words** - "show", "list", "find", "give", "tell"
3. **Include context** - "awarded contracts", "qualified vendors"
4. **Ask naturally** - Write like you're talking to a person

---

## 📈 Example Complete Queries

### Vendor Queries:
```
"What are the active vendors in our system?"
"How many active vendors are registered?"
"Show inactive vendors"
"Vendor details ABC Traders"
"Vendor info VEND001"
"Can you list all vendor details?"
"Show me the vendor master"
"Who are the registered suppliers?"
```

### Contract Queries:
```
"Show me all contracts"
"What's the total contract value?"
"Which vendors have been awarded?"
"List all signed contracts"
```

### Tender Queries:
```
"Show me published tenders"
"List tender details"
"Which tenders are open for bidding?"
"Show closed tender details"
"How many bid open tenders are there?"
```

### Bid Queries:
```
"What's the technical bid evaluation status?"
"How many bids qualified?"
"Show qualified technical bids"
"List pending technical bids"
"Which vendors failed technical evaluation?"
"Show financial bid details"
"Which bids are still sealed?"
```

### MPR Queries:
```
"Show me pending purchase requests"
"What high-priority requests are there?"
"List all approved MPRs"
"How many approved MPRs are there?"
"Show rejected MPRs"
"How many items are in this request?"
```

---

## 🚀 API Testing

You can test these queries using the API:

```bash
# Start the server
./start_chatbot.sh

# Test a query
curl -X POST http://localhost:8950/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "vendor details", "use_database": true}'
```

---

## 📊 Response Format

All responses follow this format:

```markdown
## Procurement System Summary
I analyzed the procurement database and found information related to your query.

### [Topic Overview]
[Summary with key numbers]

### [Status/Distribution Section]
- Item 1: count
- Item 2: count

### [Key Observations]
- Observation 1
- Observation 2
```

---

## ✅ Troubleshooting

### If a query doesn't work:

1. **Use simpler terms** - "contracts" instead of "purchase agreements"
2. **Add context** - "show me contracts" instead of "contracts"
3. **Check spelling** - "vendors" not "vendor's"
4. **Try variations** - "list", "show", "find" for the same data

### Common issues:

| Issue | Solution |
|-------|----------|
| No results returned | Try broader query like "vendor details" |
| Error message | Check for special characters or SQL keywords |
| Partial results | Query matched multiple tables, try more specific |
| Empty response | Table may not have data, try different table |

---

## 📞 Support

If you encounter issues:
1. Check this list for similar queries
2. Simplify your question
3. Use specific table/field names
4. Check database connectivity

**Status**: ✅ All 8 database tables supported, 50+ question variations tested

---

**Last Updated**: May 29, 2026
