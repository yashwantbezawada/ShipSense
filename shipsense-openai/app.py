from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv
from langchain import OpenAI
from langchain_experimental.sql import SQLDatabaseChain
from langchain.sql_database import SQLDatabase
from sqlalchemy.exc import SQLAlchemyError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Initialize OpenAI, Sentence Transformers, Elasticsearch, and LangChain
openai_api_key = os.getenv('OPENAI_API_KEY')
model = SentenceTransformer('all-MiniLM-L6-v2')
es = Elasticsearch([{'host': os.getenv('ES_HOST', 'localhost'), 'port': os.getenv('ES_PORT', '9200')}])

# Initialize LangChain components
llm = OpenAI(api_key=openai_api_key)
sql_database = SQLDatabase.from_uri(
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@localhost/{os.getenv('MYSQL_DB')}")
db_chain = SQLDatabaseChain(llm=llm, database=sql_database)


def get_top_documents(query):
    response = es.search(
        index='pdf_index',
        body={
            'query': {
                'multi_match': {
                    'query': query,
                    'fields': ['content^2', 'content.ngram']
                }
            },
            'size': 5,
            '_source': ['content']
        }
    )
    hits = response['hits']['hits']
    return [hit['_source']['content'] for hit in hits if '_source' in hit and 'content' in hit['_source']]


# Semantic Search Endpoint
@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query')

    # Retrieve top documents from Elasticsearch using BM25
    try:
        documents = get_top_documents(query)

        if not documents:
            return jsonify({'answer': 'No relevant documents found.'})

        # Combine the retrieved documents into a single context
        context = "\n\n".join(documents[:3])  # Limit to top 3 documents for coherence
        print(context)
        # Generate a response using the LLM
        prompt = f"Answer the following question based on the context below:\n\nContext:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        response = llm(prompt=prompt)

        return jsonify({'answer': response})
    except Exception as e:
        logging.error(f"Search query failed: {e}")
        return jsonify({'error': str(e)}), 500


# Ask Endpoint
@app.route('/ask', methods=['POST'])
def ask():
    query = request.json.get('query')

    try:
        # Use LangChain to generate and execute the SQL query
        result = db_chain.run(query)
        return jsonify(result)
    except SQLAlchemyError as e:
        logging.error(f"SQL query failed: {e}")
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True)
