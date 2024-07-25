from flask import Flask, render_template, request, jsonify, session
import os
import openai
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine
import logging
from langchain.llms import OpenAI
from langchain_experimental.sql import SQLDatabaseChain
from langchain.sql_database import SQLDatabase

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)


# Initialize Azure Cognitive Search
search_service_endpoint = os.getenv('SEARCH_SERVICE_ENDPOINT')
search_service_api_key = os.getenv('SEARCH_SERVICE_API_KEY')
search_index_name = os.getenv('SEARCH_INDEX_NAME')
search_client = SearchClient(endpoint=search_service_endpoint, index_name=search_index_name,
                             credential=AzureKeyCredential(search_service_api_key))

# Initialize Public OpenAI API
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize Azure SQL Database
db_connection_string = os.getenv('SQL_CONNECTION_STRING')
if not db_connection_string:
    logging.error("SQL_CONNECTION_STRING is not set. Please check your .env file.")
    exit(1)

# Initialize the SQLAlchemy engine
try:
    engine = create_engine(db_connection_string)
    logging.info("Successfully connected to the database")
except Exception as e:
    logging.error(f"Failed to connect to the database: {e}")
    exit(1)

# Initialize LangChain components
llm = OpenAI(api_key=openai.api_key)
sql_database = SQLDatabase.from_uri(db_connection_string)
db_chain = SQLDatabaseChain(llm=llm, database=sql_database)


def get_top_documents(query):
    logging.info("Fetching top documents for query: %s", query)
    results = search_client.search(search_text=query, select=['content'], top=200)
    documents = [doc['content'] for doc in results]
    logging.info("Retrieved %d documents", len(documents))
    return documents


@app.route('/')
def index():
    return render_template("index.html")


# Semantic Search Endpoint
@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query')
    logging.info("Received search request with query: %s", query)

    try:
        documents = get_top_documents(query)

        if not documents:
            logging.info("No relevant documents found for query: %s", query)
            return jsonify({'answer': 'No relevant documents found.'})

        # Retrieve chat history from the session
        data = request.json
        query = data.get('query')
        chat_history = data.get('chat_history', [])
        logging.info("Received search request with query: %s", query)
        logging.info("Received chat history: %s", chat_history)
        chat_history = data.get('chat_history', [])

        print(chat_history)
        # Construct the prompt with chat history and context
        history_context = "\n".join([f"User: {entry['user']}\nAssistant: {entry['assistant']}" for entry in chat_history])
        print(history_context)
        context = "\n\n".join(documents)  # Limit to top 3 documents for coherence

        logging.info("Context for OpenAI prompt: %s", context)
        prompt = f"You are a FedEx Chatbot Assitant. Based on given context and conversation between you the assitant and the user answer the following question :\n\nContext:\n{context}\n\nChat History:\n{history_context}\n\nQuestion: {query}\n\nAnswer:"

        response = llm(prompt=prompt)


        logging.info("OpenAI response: %s", response)
        return jsonify({'answer': response})
    except Exception as e:
        logging.error("Search query failed: %s", e)
        return jsonify({'error': str(e)}), 500


# Ask Endpoint
@app.route('/ask', methods=['POST'])
def ask():
    query = request.json.get('query')
    logging.info("Received ask request with query: %s", query)

    try:
        # Use LangChain to generate and execute the SQL query
        result = db_chain.run(query)
        logging.info("SQL query executed successfully, retrieved result: %s", result)
        return jsonify(result)
    except SQLAlchemyError as e:
        logging.error("SQL query failed: %s", e)
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error("An error occurred: %s", e)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logging.info("Starting Flask app")
    app.run(debug=True)