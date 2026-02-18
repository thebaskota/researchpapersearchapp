#!/usr/bin/env python3
"""
Streamlit web app for semantic paper search
"""
import json
import streamlit as st
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from collections import defaultdict
from pathlib import Path

PERSIST_DIR = Path("out_main/chroma")
COLLECTION_NAME = "projects"

@st.cache_resource
def load_collection():
    """Load ChromaDB collection (cached for performance)"""
    try:
        if not PERSIST_DIR.exists():
            st.error(f"ChromaDB directory not found: {PERSIST_DIR}")
            st.stop()
        
        embed_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        client = chromadb.PersistentClient(path=str(PERSIST_DIR))
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embed_fn,
        )
        return collection
    except Exception as e:
        st.error(f"Error loading ChromaDB collection: {str(e)}")
        st.error(f"Please ensure the ChromaDB index exists in {PERSIST_DIR}")
        st.stop()

def search_papers(query_text: str, top_k: int = 10):
    """Search for similar papers"""
    collection = load_collection()
    
    res = collection.query(
        query_texts=[query_text],
        n_results=top_k,
        include=["metadatas", "documents", "distances"],
    )
    
    return res

def main():
    st.set_page_config(
        page_title="Paper Finder",
        page_icon="📚",
        layout="wide"
    )
    
    # Debugging: Show that app started
    st.sidebar.success("✅ App loaded successfully!")
    
    st.title("📚 Paper & Expert Finder")
    st.markdown("Semantic search across research papers to find relevant work and expertise")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        top_k = st.slider("Number of results", min_value=1, max_value=20, value=10)
        
        st.markdown("---")
        st.markdown("### Example Queries")
        examples = [
            "image processing and satellite imagery",
            "algebraic geometry and prime ideals",
            "finite difference methods",
            "deconvolution and inverse problems",
            "Clifford algebras and number theory"
        ]
        for ex in examples:
            if st.button(ex, key=ex):
                st.session_state.query = ex
    
    # Main search area
    query = st.text_input(
        "🔍 Search for papers or skills:",
        value=st.session_state.get("query", ""),
        placeholder="e.g., machine learning, computational geometry, image processing..."
    )
    
    if query:
        with st.spinner("🔎 Searching..."):
            res = search_papers(query, top_k)
            
            ids = res["ids"][0]
            metas = res["metadatas"][0]
            dists = res["distances"][0]
            
            if not ids:
                st.warning("No results found. Try a different query.")
                return
            
            # Calculate employee scores
            employee_scores = defaultdict(float)
            employee_evidence = defaultdict(list)
            
            for doc_id, md, dist in zip(ids, metas, dists):
                sim = 1.0 - float(dist)
                authors = json.loads(md.get("authors_json", "[]"))
                
                for author in authors:
                    employee_scores[author] += sim
                    employee_evidence[author].append({
                        "doc_id": doc_id,
                        "title": md.get("title", ""),
                        "sim": round(sim, 3)
                    })
            
            # Display results in tabs
            tab1, tab2 = st.tabs(["📄 Papers", "👥 Experts"])
            
            with tab1:
                st.subheader(f"Top {len(ids)} Similar Papers")
                
                for rank, (doc_id, md, dist) in enumerate(zip(ids, metas, dists), start=1):
                    sim = 1.0 - float(dist)
                    title = md.get("title", "Untitled")
                    filename = md.get("filename", "")
                    authors = json.loads(md.get("authors_json", "[]"))
                    year = md.get("year", "")
                    
                    # Color-code by similarity
                    if sim > 0.4:
                        color = "🟢"
                    elif sim > 0.2:
                        color = "🟡"
                    else:
                        color = "🔴"
                    
                    with st.expander(f"{color} **{rank}. {title}** (similarity: {sim:.3f})", expanded=(rank <= 3)):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            if authors:
                                st.markdown(f"**Authors:** {', '.join(authors)}")
                            if year:
                                st.markdown(f"**Year:** {year}")
                            st.markdown(f"**File:** `{filename}`")
                        
                        with col2:
                            st.metric("Similarity", f"{sim:.1%}")
                        
                        # PDF download option
                        pdf_path = md.get("path", "")
                        if pdf_path and Path(pdf_path).exists():
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button(
                                    label="📥 Download PDF",
                                    data=pdf_file,
                                    file_name=filename,
                                    mime="application/pdf",
                                    key=f"download_{doc_id}",
                                    use_container_width=True
                                )
            
            with tab2:
                st.subheader("Top Experts by Cumulative Similarity")
                
                ranked = sorted(employee_scores.items(), key=lambda x: x[1], reverse=True)
                
                for i, (name, score) in enumerate(ranked[:10], start=1):
                    evidence = employee_evidence[name]
                    
                    # Color-code by score
                    if score > 1.0:
                        color = "🟢"
                    elif score > 0.5:
                        color = "🟡"
                    else:
                        color = "🔴"
                    
                    with st.expander(f"{color} **{i}. {name}** (score: {score:.3f})", expanded=(i <= 3)):
                        st.markdown(f"**Total Relevance Score:** {score:.3f}")
                        st.markdown(f"**Number of Relevant Papers:** {len(evidence)}")
                        
                        st.markdown("**Top Papers:**")
                        for j, ev in enumerate(evidence[:5], 1):
                            st.markdown(f"{j}. {ev['title']} (sim: {ev['sim']:.3f})")
    
    else:
        # Welcome screen
        st.info("👆 Enter a search query above or click an example in the sidebar to get started!")
        
        st.markdown("### How it works:")
        st.markdown("""
        1. **Enter a query** describing research topics, skills, or keywords
        2. **View papers** ranked by semantic similarity to your query
        3. **Find experts** ranked by their cumulative relevance across papers
        
        The system uses AI embeddings to understand meaning, not just keywords!
        """)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

