import os
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch.helpers import bulk
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Initialize Sentence Transformers model and Elasticsearch client
model = SentenceTransformer('all-MiniLM-L6-v2')
es_host = os.getenv('ES_HOST', 'localhost')
es_port = os.getenv('ES_PORT', '9200')
es = Elasticsearch(
    [{'host': es_host, 'port': es_port}],
    connection_class=RequestsHttpConnection,
    headers={"Content-Type": "application/json"}
)

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text += page.get_text()
    return text

def index_text_in_elasticsearch(text, pdf_filename):
    actions = []
    paragraphs = text.split('\n')
    for i, paragraph in enumerate(paragraphs):
        if paragraph.strip():  # Index non-empty paragraphs
            action = {
                "_index": "pdf_index",
                "_id": f"{pdf_filename}_{i}",
                "_source": {
                    'pdf_filename': pdf_filename,
                    'content': paragraph,
                    'embedding': model.encode(paragraph).tolist()
                }
            }
            actions.append(action)
    if actions:
        bulk(es, actions)
        logging.info(f"Indexed {len(actions)} paragraphs from {pdf_filename}")

def index_pdfs_in_directory(directory_path):
    total_files = len([name for name in os.listdir(directory_path) if name.endswith('.pdf')])
    logging.info(f"Found {total_files} PDF files in directory {directory_path}")

    for filename in os.listdir(directory_path):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(directory_path, filename)
            logging.info(f"Extracting text from {filename}")
            text = extract_text_from_pdf(pdf_path)
            index_text_in_elasticsearch(text, filename)
            logging.info(f"Completed indexing for {filename}")

if __name__ == "__main__":
    directory_path = 'knowledgebase'  # Directory containing the PDF files
    index_pdfs_in_directory(directory_path)
