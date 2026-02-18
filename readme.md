# 📚 Research Paper & Expert Finder

A semantic search system for academic papers that helps find relevant research and identify expert researchers by topic.

## 🎯 What It Does

- **Semantic Search**: Find papers by meaning, not just keywords
- **Expert Ranking**: Identify researchers by cumulative relevance across papers
- **Interactive Web UI**: Clean Streamlit interface for easy searching

> **Note:** PDF files are not included in the repository to keep it lightweight. The system works with the pre-extracted metadata and ChromaDB index.

## 🏗️ Architecture

```
PDFs → Text Extraction (PyMuPDF)
    → LLM Metadata Extraction (Ollama + Llama 3.2)
    → Structured JSON
    → Vector Embeddings (SentenceTransformers)
    → ChromaDB Index
    → Streamlit Web App
```

## 📊 Current Dataset

- **26 academic papers** (PDF format)
- **5 main authors**: Amelia Carolina Sparavigna, Alberto Corso, A.J. Roberts, Alexander G. Ramm, A.K. Kwasniewski
- **Topics**: Image processing, algebraic geometry, numerical methods, mathematical analysis, combinatorics

---

## 🚀 Quick Start

### Prerequisites
```bash
# Install Ollama
brew install ollama  # macOS
# or download from https://ollama.ai

# Pull the model
ollama pull llama3.2:3b

# Start Ollama server (in separate terminal)
ollama serve
```

### Installation
```bash
# Clone repository
git clone <your-repo-url>
cd makerton

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the System

**Step 1: Extract metadata from PDFs**
```bash
python 1_initial_script.py
# Extracts: title, authors, year, abstract, keywords, categories
# Output: out_main/json/*.json
```

**Step 2: Build ChromaDB index**
```bash
python 3_build_chroma_index.py
# Creates vector embeddings and indexes papers
# Output: out_main/chroma/
```

**Step 3: Web interface (recommended)**
```bash
streamlit run app.py
# Opens at http://localhost:8501
```

**OR use command-line query**
```bash
python 4_query.py "image processing and satellite imagery"
python 4_query.py "algebraic geometry" 10  # return top 10
```

---

## 📁 Project Structure

```
makerton/
├── data/                           # Input PDFs
├── out_main/
│   ├── json/                       # Extracted metadata (26 files)
│   ├── chroma/                     # ChromaDB vector database
│   └── metadata_log.json           # Index log
├── 1_initial_script.py             # PDF → JSON extraction
├── 2_skill_extractor.py            # Alternative extractor
├── 3_build_chroma_index.py         # Build vector index
├── 4_query.py                      # CLI search tool
├── app.py                          # Streamlit web app
├── requirements.txt                # Python dependencies
└── DEPLOYMENT.md                   # Deployment guide
```

---

## 🔍 How It Works

### 1. Metadata Extraction
- Reads first 2-4 pages of each PDF
- Uses Llama 3.2 (3B) via Ollama to extract:
  - Title
  - Authors
  - Year
  - Abstract
  - Keywords (3-12 phrases)
  - Categories (2-8 broad areas)

### 2. Vector Indexing
- Combines title, abstract, keywords, categories into text
- Generates embeddings using `all-MiniLM-L6-v2` (SentenceTransformer)
- Stores in ChromaDB with cosine similarity metric
- Metadata includes: filename, path, year, authors, title

### 3. Semantic Search
- Query text → embedding
- ChromaDB finds top-k similar papers by cosine distance
- Converts distance to similarity score (0-1)
- Ranks authors by cumulative similarity across papers

---

## 🌐 Deployment

The app is ready to deploy on **Streamlit Cloud** (free):

1. Push code to GitHub
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Deploy `app.py`
5. Get live URL: `https://your-app.streamlit.app`

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

---

## 🎨 Web Interface Features

- **Search box** with example queries
- **Paper results** with:
  - Similarity scores (color-coded)
  - Title, authors, year
  - Download PDF button
  - View PDF inline button
- **Expert rankings** with:
  - Cumulative relevance scores
  - Top papers as evidence
  - Number of relevant papers

---

## 🔧 Technology Stack

| Component | Technology |
|-----------|-----------|
| PDF Processing | PyMuPDF (fitz) |
| LLM | Ollama + Llama 3.2 (3B) |
| Embeddings | SentenceTransformers (all-MiniLM-L6-v2) |
| Vector DB | ChromaDB |
| Web Framework | Streamlit |
| Language | Python 3.9+ |

---

## 📈 Example Queries

```bash
# Image processing papers
python 4_query.py "image processing and satellite imagery"

# Algebraic geometry
python 4_query.py "algebraic geometry prime ideals commutative algebra"

# Numerical methods
python 4_query.py "finite difference methods numerical analysis"

# Mathematical analysis
python 4_query.py "deconvolution scattering inverse problems"

# Combinatorics
python 4_query.py "recurrence relations Fibonacci combinatorics"
```

---

## 🛠️ Customization

### Add More Papers
1. Place PDFs in `data/` folder
2. Run extraction: `python 1_initial_script.py`
3. Rebuild index: `python 3_build_chroma_index.py`
4. Restart web app

### Adjust Search Parameters
Edit `app.py`:
- Change `top_k` slider range
- Modify example queries
- Customize UI theme

### Change Embedding Model
Edit `3_build_chroma_index.py` and `4_query.py`:
```python
embed_fn = SentenceTransformerEmbeddingFunction(
    model_name="all-mpnet-base-v2"  # More accurate but slower
)
```

---

## 📝 License

MIT

---

## 🤝 Contributing

Pull requests welcome!

---

## 📧 Support

For issues, please open a GitHub issue.

