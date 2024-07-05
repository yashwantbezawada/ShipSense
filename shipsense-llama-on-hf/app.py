from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv
import logging
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Hugging Face inference API details
hf_endpoint = os.getenv('HF_ENDPOINT')
hf_token = os.getenv('HF_TOKEN')
mysql_user = os.getenv('MYSQL_USER')
mysql_password = os.getenv('MYSQL_PASSWORD')
mysql_db = os.getenv('MYSQL_DB')

# Verify environment variables
logging.info(f"Hugging Face Endpoint: {hf_endpoint}")
logging.info(f"Hugging Face Token: {'Loaded' if hf_token else 'Not Loaded'}")
logging.info(f"MySQL User: {mysql_user}")
logging.info(f"MySQL Database: {mysql_db}")

app = Flask(__name__)

# Initialize Sentence Transformers and Elasticsearch
model = SentenceTransformer('all-MiniLM-L6-v2')
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

# Database engine
engine = create_engine(f"mysql+pymysql://{mysql_user}:{mysql_password}@localhost/{mysql_db}")

# Function to get top documents from Elasticsearch
def get_top_documents(query, top_n=5):
    logging.info(f"Fetching top documents for query: {query}")
    try:
        response = es.search(
            index='pdf_index',
            body={
                'query': {
                    'multi_match': {
                        'query': query,
                        'fields': ['content^2', 'content.ngram']
                    }
                },
                'size': top_n,
                '_source': ['content']
            }
        )
        hits = response['hits']['hits']
        documents = [hit['_source']['content'] for hit in hits if '_source' in hit and 'content' in hit['_source']]
        logging.info(f"Retrieved {len(documents)} documents")
        return documents
    except Exception as e:
        logging.error(f"Error fetching documents: {e}")
        return []

# Function to call the Hugging Face inference endpoint
def call_hf_inference(prompt):
    headers = {
        'Authorization': f'Bearer {hf_token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'inputs': prompt,
        'parameters': {'max_length': 512, 'return_full_text': False}
    }
    response = requests.post(hf_endpoint, headers=headers, json=payload)
    if response.status_code == 200:
        try:
            result = response.json()
            # Handle the case where the result might be a list or dict
            if isinstance(result, list):
                generated_text = result[0].get('generated_text', '')
            elif isinstance(result, dict):
                generated_text = result.get('generated_text', '')
            return generated_text
        except (IndexError, KeyError, TypeError) as e:
            logging.error(f"Unexpected response format from Hugging Face: {response.json()}")
            return "Sorry, I couldn't process your request."
    else:
        logging.error(f"Failed to get a response from Hugging Face: {response.text}")
        return "Sorry, I couldn't process your request."

# Function to execute SQL query
def execute_sql_query(sql_query):
    logging.info(f"Executing SQL query: {sql_query}")
    try:
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            rows = result.fetchall()
            logging.info(f"SQL query result: {rows}")
            return [dict(row) for row in rows]
    except SQLAlchemyError as e:
        logging.error(f"SQL query failed: {e}")
        raise

# Semantic Search Endpoint
@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query')
    logging.info(f"Received search query: {query}")
    try:
        # Retrieve top documents from Elasticsearch
        documents = get_top_documents(query)

        if not documents:
            logging.info("No relevant documents found.")
            return jsonify({'answer': 'No relevant documents found.'})

        # Combine the retrieved documents into a single context
        context = "\n\n".join(documents[:3])  # Limit to top 3 documents for coherence
        logging.info(f"Context for Hugging Face API: {context}")

        # Generate a response using Hugging Face's LLaMA
        prompt = f"Answer the following question based on the context below:\n\nContext:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        answer = call_hf_inference(prompt)

        return jsonify({'answer': answer})
    except Exception as e:
        logging.error(f"Search query failed: {e}")
        return jsonify({'error': str(e)}), 500

# Ask Endpoint
@app.route('/ask', methods=['POST'])
def ask():
    query = request.json.get('query')
    logging.info(f"Received ask query: {query}")
    try:
        # Generate the SQL query using Hugging Face's LLaMA
        prompt = f"Generate an SQL query to answer the following question. Your output should only be a SQL query and nothing else. The table is called package and Here is the table schema for reference: id | tracking_number | dimensions | weight | status | eta | last_update :\n\nQuestion: {query}\n\nSQL Query:"
        logging.info(f"prompt: {prompt}")
        sql_query = call_hf_inference(prompt).strip()  # Ensure to strip any extra spaces
        logging.info(f"Generated SQL query: {sql_query}")

        # Execute the generated SQL query
        result = execute_sql_query(sql_query)

        logging.info(f"SQL query result: {result}")
        return jsonify(result)
    except SQLAlchemyError as e:
        logging.error(f"SQL query failed: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Ask query failed: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
