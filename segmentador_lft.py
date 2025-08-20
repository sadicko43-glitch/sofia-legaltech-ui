import fitz  # PyMuPDF
import re

def cargar_articulos_lft(path_pdf="LFT.pdf"):
    doc = fitz.open(path_pdf)
    texto = "\n".join([page.get_text() for page in doc])
    articulos = re.findall(r"(Artículo\s+\d+[\s\S]*?)(?=Artículo\s+\d+|$)", texto)
    return {f"Artículo {i+1}": art.strip() for i, art in enumerate(articulos)}
