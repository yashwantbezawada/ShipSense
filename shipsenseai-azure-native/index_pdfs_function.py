import os
import fitz  # PyMuPDF
import camelot
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import logging
import json
import base64

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables
BLOB_CONNECTION_STRING = os.getenv('BLOB_CONNECTION_STRING')
SEARCH_SERVICE_ENDPOINT = os.getenv('SEARCH_SERVICE_ENDPOINT')
SEARCH_SERVICE_API_KEY = os.getenv('SEARCH_SERVICE_API_KEY')
SEARCH_INDEX_NAME = os.getenv('SEARCH_INDEX_NAME')

# Ensure the BLOB_CONNECTION_STRING is set
if not BLOB_CONNECTION_STRING:
    logging.error("BLOB_CONNECTION_STRING is not set or is malformed. Please check your .env file.")
    exit(1)

# Log the connection string (optional for debugging)
logging.info(f"BLOB_CONNECTION_STRING: {BLOB_CONNECTION_STRING}")
logging.info(f"SEARCH_SERVICE_ENDPOINT: {SEARCH_SERVICE_ENDPOINT}")
logging.info(f"SEARCH_SERVICE_API_KEY: {SEARCH_SERVICE_API_KEY}")
logging.info(f"SEARCH_INDEX_NAME: {SEARCH_INDEX_NAME}")

# Initialize BlobServiceClient
try:
    blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
    logging.info("Successfully connected to Azure Blob Storage")
except ValueError as e:
    logging.error(f"Failed to connect to Azure Blob Storage: {e}")
    exit(1)

# Initialize SearchClient
search_client = SearchClient(endpoint=SEARCH_SERVICE_ENDPOINT, index_name=SEARCH_INDEX_NAME,
                             credential=AzureKeyCredential(SEARCH_SERVICE_API_KEY))

# Initialize Sentence Transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_text_from_pdf(pdf_path):
    logging.info("Extracting text from PDF: %s", pdf_path)
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text += page.get_text()
        logging.info("Extracted text from PDF: %s", pdf_path)
        return text
    except Exception as e:
        logging.error(f"Failed to extract text from PDF {pdf_path}: {e}")
        return ""

def extract_tables_from_pdf(pdf_path):
    logging.info("Extracting tables from PDF: %s", pdf_path)
    try:
        tables = camelot.read_pdf(pdf_path, pages='all')
        table_data = [table.df.to_dict(orient='records') for table in tables]
        logging.info("Extracted %d tables from PDF: %s", len(tables), pdf_path)
        return table_data
    except Exception as e:
        logging.error(f"Failed to extract tables from PDF {pdf_path}: {e}")
        return []

def encode_document_key(key):
    # Encode the document key using URL-safe Base64 encoding
    encoded_bytes = base64.urlsafe_b64encode(key.encode('utf-8'))
    encoded_str = encoded_bytes.decode('utf-8')
    return encoded_str.rstrip('=')

def index_text_and_tables_in_search(text, tables, pdf_filename):
    logging.info("Indexing text and tables from PDF: %s", pdf_filename)
    paragraphs = text.split('\n')
    actions = []

    # Index textual data
    for i, paragraph in enumerate(paragraphs):
        if paragraph.strip():  # Index non-empty paragraphs
            embedding = model.encode(paragraph).tolist()
            document = {
                'id': encode_document_key(f"{pdf_filename}_text_{i}"),
                'pdf_filename': pdf_filename,
                'content': paragraph,
                'embedding': embedding
            }
            actions.append(document)

    # Index tabular data
    for i, table in enumerate(tables):
        table_json = json.dumps(table)
        embedding = model.encode(table_json).tolist()
        document = {
            'id': encode_document_key(f"{pdf_filename}_table_{i}"),
            'pdf_filename': pdf_filename,
            'content': table_json,
            'embedding': embedding
        }
        actions.append(document)

    # Break actions into smaller chunks and upload
    chunk_size = 1000
    for i in range(0, len(actions), chunk_size):
        chunk = actions[i:i+chunk_size]
        try:
            search_client.upload_documents(chunk)
            logging.info("Indexed %d documents from %s", len(chunk), pdf_filename)
        except Exception as e:
            logging.error(f"Failed to index chunk of documents from PDF {pdf_filename}: {e}")

def index_pdfs_in_blob_storage(container_name):
    logging.info("Indexing PDFs in blob storage container: %s", container_name)
    container_client = blob_service_client.get_container_client(container_name)
    blobs = container_client.list_blobs()
    for blob in blobs:
        if blob.name.endswith('.pdf'):
            logging.info("Processing blob: %s", blob.name)
            try:
                pdf_blob = container_client.get_blob_client(blob).download_blob().readall()
                pdf_path = f"/tmp/{blob.name}"
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_blob)
                text = extract_text_from_pdf(pdf_path)
                tables = extract_tables_from_pdf(pdf_path)
                index_text_and_tables_in_search(text, tables, blob.name)
                os.remove(pdf_path)
                logging.info("Completed processing blob: %s", blob.name)
            except Exception as e:
                logging.error(f"Failed to process blob {blob.name}: {e}")

if __name__ == "__main__":
    logging.info("Starting PDF indexing process")
    index_pdfs_in_blob_storage('your-container-name')
