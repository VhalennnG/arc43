# arc43 — AI-Powered Form Auto-Fill

**arc43** is a local, privacy-first macOS application designed to automatically fill out target forms using information from your own personal documents (such as resumes, ID cards, tax forms, or spreadsheets). 

All file processing, text extraction, optical character recognition (OCR), and artificial intelligence (AI) inference are performed **100% locally on your device**. None of your personal data is ever uploaded to the cloud or sent to third-party services.

---

## 🌟 Key Features

*   **100% On-Device Privacy**: Your documents and personal data stay secure on your local machine.
*   **Multi-Format Ingestion**: Supports extracting text from PDFs, images (PNG, JPG, etc.), Word documents (DOCX), and Excel spreadsheets (XLSX).
*   **Smart Fallback OCR**: Automatically triggers macOS-native Apple Vision OCR for scanned PDFs and image files.
*   **Automated Form Matching**: Uses a local AI model to extract required form values verbatim from your personal files.
*   **Interactive Review**: Displays extracted answers in a clean table, allowing you to edit and verify before generating the final form.

---

## 💻 User Guide (How to Use)

The application features a clean, responsive web interface divided into two main tabs:

### Tab 1: Knowledge Base (Your Information Sources)

This tab is where you manage the documents that contain your personal information.

1. **Upload Source Documents**: Click the upload area to select documents such as your resume, ID documents, or transcript.
2. **Automatic Text Extraction**: The app parses the document text. If the document is an image or scan, macOS Vision OCR extracts the text.
3. **AI Classification**: A local AI model classifies the document (e.g., *"Personal information containing Resume"*).
4. **View Documents**: Your document list is saved locally and can be viewed or selected for form-filling.

### Tab 2: Auto-Fill Form (Filling Your Templates)

This tab handles the automated form-filling pipeline.

1. **Select Sources**: Check the boxes of the documents in your Knowledge Base that you want to use as references.
2. **Upload a Blank Form**: Upload the target empty form template you want to fill out.
3. **Match Fields**: The system scans the form, extracts the required field names, and queries the local AI to search your reference documents for matching answers.
4. **Review & Edit**: Review the AI-generated answers in the interactive table. You can manually edit any values if needed.
5. **Download the Filled Form**: Click "Submit" to write the values into the form. You can then download your completed document immediately.

---

## 📊 Application Workflows

Here is how data flows through the application during key operations:

### 1. Document Ingestion Flow (Tab 1)

This diagram shows how your uploaded source documents are parsed, processed by local AI, and saved to your secure offline database:

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant UI as Browser UI (HTMX)
    participant App as FastAPI Server (app.py)
    participant Pars as Document Parsers (parsers.py)
    participant OCR as macOS Vision OCR (ocr.py)
    participant LLM as Sequential LLM (llm.py)
    participant DB as Local Database (db.py)

    User->>UI: Upload Source File (PDF/Image/Word/Excel)
    UI->>App: HTTP POST /upload-doc (Multipart File)
    Note over App: Save temporarily in temp_uploads/

    App->>Pars: parse_document(file_path)

    alt If PDF has digital text layer
        Pars->>Pars: Extract via pypdf
    else If PDF is empty (Scan) or Image
        Pars->>OCR: recognize_pdf_text_via_ocr() / recognize_text()
        Note over OCR: Render PDFPage to NSImage (Quartz)
        OCR->>OCR: Extract text via Apple Vision OCR API
        OCR-->>Pars: Return verbatim raw_text
    end

    Pars-->>App: Return raw_text & extraction_method

    App->>LLM: generate_text(classification_prompt)
    Note over LLM: Load Apertus GGUF model into RAM
    LLM->>LLM: Classify document category (1 sentence)
    Note over LLM: Unload model from RAM (Free Memory)
    LLM-->>App: Return category text

    App->>DB: save_record(filename, category, raw_text)
    Note over DB: Write .txt file in data/knowledge/<br/>Update index.json
    DB-->>App: Return meta record

    Note over App: Delete file in temp_uploads/
    App->>UI: Return rendered Tab 1 HTML template
    UI->>User: Update Document List UI
```

### 2. Auto-Fill Pipeline Flow (Tab 2)

This flowchart illustrates the step-by-step process of parsing templates, matching fields via local AI context, and generating the final output:

```mermaid
flowchart TD
    %% Node Definitions
    A[📄 Upload Source Documents <br/> PDF / Image / DOCX / XLSX] --> B{🔍 Raw Text Extraction}

    %% Format Router Decisions
    B -->|Digital Parser| C[⚙️ Programmatic Parser <br/> pypdf / python-docx / openpyxl]
    B -->|Image or Scanned PDF| D[👁️ macOS Vision OCR <br/> Native Apple OCR Engine]

    C --> E[📝 Extracted Raw Text]
    D --> E

    E --> F[🧠 Category Classification <br/> Local LLM Apertus-8B]
    F --> G[(💾 Local Storage <br/> data/knowledge/ *.txt & index.json)]

    %% Tab 2 Pipeline
    H[📄 Upload Blank Form Template] --> I{⚡ Fillable Field Detection}
    I -->| fill_form stubs | J[📋 Detect Input Fields <br/> fillers.detect_fields]

    G --> K[🤖 Context-Prefixed LLM Search]
    J --> K
    K --> L[✏️ User Review & Edit Fields]
    L --> M[🖨️ Final Document Generator]
    M --> N[(📥 Auto-Filled Output <br/> data/outputs/ filled_*)]

    %% Styling
    style A fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff
    style B fill:#334155,stroke:#94a3b8,stroke-width:2px,color:#fff
    style C fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff
    style D fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff
    style E fill:#0284c7,stroke:#bae6fd,stroke-width:2px,color:#fff
    style F fill:#6366f1,stroke:#c7d2fe,stroke-width:2px,color:#fff
    style G fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff
    style H fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff
    style I fill:#334155,stroke:#94a3b8,stroke-width:2px,color:#fff
    style J fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff
    style K fill:#6366f1,stroke:#c7d2fe,stroke-width:2px,color:#fff
    style L fill:#0284c7,stroke:#bae6fd,stroke-width:2px,color:#fff
    style M fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff
    style N fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff
```

---

## 🛠️ Developer Setup & Technical details

If you are a developer, want to configure advanced environment settings (`.env`), inspect the code directory structure, or run the local test suites, please refer to the detailed technical documentation:

👉 **[System Architecture & Developer Guide (ARCHITECTURE.md)](ARCHITECTURE.md)**
