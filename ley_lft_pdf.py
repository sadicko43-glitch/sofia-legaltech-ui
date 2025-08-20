import requests, fitz, re
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

URL_PDF = "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf"

def descargar_pdf(ruta="LFT.pdf"):
    response = requests.get(URL_PDF)
    if response.status_code == 200:
        with open(ruta, "wb") as f:
            f.write(response.content)
        return ruta
    raise Exception(f"Error al descargar PDF: {response.status_code}")

def extraer_texto_pdf(ruta="LFT.pdf"):
    doc = fitz.open(ruta)
    texto = ""
    for page in doc:
        texto += page.get_text()
    return texto

def segmentar_articulos(texto):
    patron = r"(Artículo\s+\d+[^\n]*\n[\s\S]*?)(?=Artículo\s+\d+|$)"
    return re.findall(patron, texto)

def generar_embeddings(articulos):
    modelo = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    vectores = modelo.encode(articulos, show_progress_bar=True)
    return vectores, modelo

def indexar_faiss(vectores):
    dim = len(vectores[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(vectores))
    return index

def buscar_articulos(query, modelo, index, articulos, top_k=3):
    vector_query = modelo.encode([query])
    _, indices = index.search(np.array(vector_query), top_k)
    return [articulos[i] for i in indices[0]]
