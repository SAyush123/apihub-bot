from flask import Flask, render_template, request, jsonify, url_for, redirect
import ollama
import json
import uuid
import datetime
import os
import time
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout

app = Flask(__name__)

# Define the path for the tickets JSON file
tickets_file = "tickets.json"
knowledge_base_file = "apihub_knowledge.txt"

# Load knowledge base
knowledge_base = ""
try:
    with open(knowledge_base_file, "r", encoding="utf-8") as file:
        knowledge_base = file.read()
    print(f"✅ Successfully loaded knowledge base from {knowledge_base_file}")
except FileNotFoundError:
    knowledge_base = "No knowledge base loaded. Please add apihub_knowledge.txt in the same directory as app.py."
    print(f"⚠️ [WARNING] Knowledge base file '{knowledge_base_file}' not found.")
except Exception as e:
    knowledge_base = "Error loading knowledge base. Please check apihub_knowledge.txt."
    print(f"❌ [ERROR] Error loading knowledge base from {knowledge_base_file}: {e}")

# Load or initialize support tickets
tickets = []
if os.path.exists(tickets_file) and os.path.getsize(tickets_file) > 0:
    try:
        with open(tickets_file, "r", encoding="utf-8") as f:
            tickets = json.load(f)
        print(f"✅ Successfully loaded {len(tickets)} tickets from {tickets_file}")
    except json.JSONDecodeError:
        print(f"⚠️ [WARNING] Couldn't decode {tickets_file}. Starting with empty ticket list.")
    except Exception as e:
        print(f"❌ [ERROR] Error loading tickets from {tickets_file}: {e}")
else:
    print(f"ℹ️ [INFO] '{tickets_file}' not found or is empty. Starting with an empty ticket list.")

def check_file_permissions():
    """Check if we can write to the current directory"""
    current_dir = os.getcwd()
    print(f"🔍 Current directory: {current_dir}")
    print(f"🔍 Directory writable: {os.access(current_dir, os.W_OK)}")
    
    if os.path.exists(tickets_file):
        print(f"🔍 {tickets_file} exists: True")
        print(f"🔍 {tickets_file} writable: {os.access(tickets_file, os.W_OK)}")
        print(f"🔍 {tickets_file} size: {os.path.getsize(tickets_file)} bytes")
    else:
        print(f"🔍 {tickets_file} exists: False")

def check_ollama_service():
    """Check if Ollama service is running and llama3 model is available"""
    try:
        # Try to connect to Ollama API
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            llama3_available = any('llama3' in model.get('name', '').lower() for model in models)
            if llama3_available:
                print("✅ Ollama service is running and llama3 model is available")
                return True
            else:
                print("⚠️ Ollama is running but llama3 model not found")
                return False
        else:
            print("❌ Ollama service responded with error")
            return False
    except (ConnectionError, Timeout, RequestException) as e:
        print(f"❌ Cannot connect to Ollama service: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error checking Ollama: {e}")
        return False

def query_llama3(user_prompt, timeout=30):
    """Query LLaMA 3 using Ollama with improved error handling and timeout"""
    
    # Check if Ollama service is available first
    if not check_ollama_service():
        print("🔍 DEBUG - Ollama not available, will create ticket")
        return "❌ Ollama service is not running or llama3 model is not available. Please start Ollama and ensure llama3 model is installed."
    
    # Enhanced prompt with clearer instructions
    full_prompt = f"""You are the APIhub Assistant Bot, a specialized support chatbot for APIhub.digital platform.

Your role:
1. Answer ONLY APIhub-related questions using the knowledge base provided
2. If a question is NOT related to APIhub services, APIs, authentication, pricing, or platform features, respond EXACTLY with: "Not related to APIhub, creating support ticket..."
3. If the knowledge base doesn't contain the answer to an APIhub question, respond EXACTLY with: "Not related to APIhub, creating support ticket..."
4. Be helpful, professional, and concise in your responses
5. Use emojis appropriately to make responses engaging

APIhub Knowledge Base:
{knowledge_base}

User Query: {user_prompt}

Response:"""

    try:
        print(f"🤖 Processing query: {user_prompt[:50]}...")
        
        # Use ollama.chat with timeout handling
        start_time = time.time()
        response = ollama.chat(
            model='llama3',
            messages=[{'role': 'user', 'content': full_prompt}],
            stream=False,
            options={
                'timeout': timeout,
                'temperature': 0.7,
                'top_p': 0.9
            }
        )
        
        processing_time = time.time() - start_time
        print(f"⏱️ Query processed in {processing_time:.2f} seconds")
        
        # Extract the content from the response
        if response and 'message' in response and 'content' in response['message']:
            result = response['message']['content'].strip()
            print(f"🎯 Bot response generated successfully")
            return result
        else:
            print("❌ [ERROR] Ollama returned an unexpected response structure.")
            return "❌ Sorry, I received an invalid response from the AI model. Let me create a support ticket for you."
            
    except ollama.ResponseError as e:
        print(f"❌ [ERROR] Ollama API error: {e}")
        return "❌ Sorry, I'm having trouble connecting to the AI model. Please ensure Ollama is running and the 'llama3' model is available."
    except Exception as e:
        print(f"❌ [ERROR] Unexpected error during LLaMA3 query: {e}")
        return "❌ Sorry, something went wrong while processing your query. Let me create a support ticket to get you proper assistance."

def create_support_ticket(user_msg, contact="N/A"):
    """Create a support ticket and save it with enhanced debugging"""
    print(f"🔍 DEBUG - Creating ticket for: '{user_msg}'")
    print(f"🔍 DEBUG - Contact info: '{contact}'")
    
    ticket = {
        "id": str(uuid.uuid4())[:8],  # Shorter ID for better UX
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query": user_msg,
        "contact": contact,
        "status": "Open",
        "priority": "Medium",
        "created_at": datetime.datetime.now().isoformat()
    }
    
    print(f"🔍 DEBUG - Ticket object created: {ticket}")
    
    tickets.append(ticket)
    print(f"🔍 DEBUG - Added to tickets list. Total tickets in memory: {len(tickets)}")
    
    try:
        print(f"🔍 DEBUG - Attempting to write to {tickets_file}")
        with open(tickets_file, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=4, ensure_ascii=False)
        
        print(f"🎫 Support ticket created successfully: {ticket['id']}")
        
        # Verify the file was written
        if os.path.exists(tickets_file):
            file_size = os.path.getsize(tickets_file)
            print(f"🔍 DEBUG - File written successfully. Size: {file_size} bytes")
        else:
            print(f"❌ DEBUG - File was not created!")
        
        return ticket
        
    except PermissionError as e:
        print(f"❌ [ERROR] Permission denied writing to {tickets_file}: {e}")
        return None
    except json.JSONEncodeError as e:
        print(f"❌ [ERROR] JSON encoding error: {e}")
        return None
    except Exception as e:
        print(f"❌ [ERROR] Failed to save ticket to {tickets_file}: {e}")
        return None

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    # Sort tickets by timestamp (newest first)
    sorted_tickets = sorted(tickets, key=lambda x: x.get('timestamp', ''), reverse=True)
    return render_template("dashboard.html", tickets=sorted_tickets)

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        user_msg = data.get("message", "").strip()
        contact = data.get("contact", "N/A")

        if not user_msg:
            return jsonify({"reply": "Please enter a valid message. How can I help you with APIhub? 🤔"})

        # Log the incoming request
        print(f"📝 Received query: '{user_msg}'")
        print(f"📝 Contact: '{contact}'")

        # Query the AI model
        response = query_llama3(user_msg)
        
        # DEBUG: Print the actual response to see what's happening
        print(f"🔍 DEBUG - AI Response: '{response}'")

        # Check for ticket creation triggers - ENHANCED CONDITIONS
        should_create_ticket = (
            "Not related to APIhub, creating support ticket..." in response or
            "❌" in response or
            "Sorry, something went wrong" in response.lower() or
            "Ollama service is not running" in response or
            "invalid response from the AI model" in response or
            "having trouble connecting" in response
        )
        
        # DEBUG: Print ticket creation decision
        print(f"🔍 DEBUG - Should create ticket: {should_create_ticket}")
        print(f"🔍 DEBUG - Response contains 'Not related': {'Not related to APIhub, creating support ticket...' in response}")
        print(f"🔍 DEBUG - Response contains ❌: {'❌' in response}")

        if should_create_ticket:
            print("🔍 DEBUG - Creating ticket...")
            ticket = create_support_ticket(user_msg, contact)
            
            if ticket:
                response_message = f"🎫 I've created support ticket #{ticket['id']} for your query. Our team will get back to you soon! In the meantime, you can check the status on our dashboard."
                return jsonify({
                    "reply": response_message,
                    "ticket": ticket,
                    "ticket_created": True
                })
            else:
                return jsonify({
                    "reply": "❌ I couldn't process your query and failed to create a support ticket. Please try again or contact our support team directly.",
                    "ticket_created": False
                })

        # Return successful AI response
        print("🔍 DEBUG - Returning AI response without creating ticket")
        return jsonify({
            "reply": response,
            "ticket_created": False
        })

    except Exception as e:
        print(f"❌ [ERROR] Error in chat endpoint: {e}")
        # Create a ticket for the error case
        ticket = create_support_ticket(user_msg if 'user_msg' in locals() else "Error occurred", 
                                     contact if 'contact' in locals() else "N/A")
        return jsonify({
            "reply": "❌ An unexpected error occurred. I've created a support ticket for you.",
            "ticket": ticket,
            "ticket_created": True,
            "error": str(e)
        }), 500

# DEBUG AND TEST ROUTES
@app.route("/test-ticket", methods=["POST", "GET"])
def test_ticket():
    """Test route to force create a ticket"""
    test_message = "This is a test ticket creation - " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🧪 Creating test ticket with message: {test_message}")
    
    ticket = create_support_ticket(test_message, "test@example.com")
    
    if ticket:
        return jsonify({
            "success": True,
            "ticket": ticket,
            "message": f"Test ticket created: {ticket['id']}",
            "total_tickets": len(tickets)
        })
    else:
        return jsonify({
            "success": False,
            "message": "Failed to create test ticket",
            "total_tickets": len(tickets)
        })

@app.route("/debug-tickets")
def debug_tickets():
    """Debug route to check ticket status"""
    file_exists = os.path.exists(tickets_file)
    file_size = os.path.getsize(tickets_file) if file_exists else 0
    
    file_content = None
    if file_exists and file_size > 0:
        try:
            with open(tickets_file, 'r') as f:
                file_content = f.read()
        except Exception as e:
            file_content = f"Error reading file: {e}"
    
    return jsonify({
        "tickets_in_memory": tickets,
        "tickets_count": len(tickets),
        "file_exists": file_exists,
        "file_size": file_size,
        "file_content_preview": file_content[:500] if file_content else None,
        "current_directory": os.getcwd(),
        "directory_writable": os.access(os.getcwd(), os.W_OK)
    })

@app.route("/force-ticket", methods=["POST"])
def force_ticket():
    """Force create a ticket regardless of AI response"""
    data = request.get_json()
    user_msg = data.get("message", "Forced ticket creation")
    contact = data.get("contact", "N/A")
    
    print(f"🔧 FORCE CREATING TICKET for: {user_msg}")
    ticket = create_support_ticket(user_msg, contact)
    
    if ticket:
        return jsonify({
            "reply": f"🎫 Forced ticket creation successful! Ticket #{ticket['id']} created.",
            "ticket": ticket,
            "ticket_created": True
        })
    else:
        return jsonify({
            "reply": "❌ Force ticket creation failed!",
            "ticket_created": False
        })

@app.route("/health")
def health_check():
    """Health check endpoint"""
    ollama_status = check_ollama_service()
    return jsonify({
        "status": "healthy" if ollama_status else "degraded",
        "ollama_available": ollama_status,
        "timestamp": datetime.datetime.now().isoformat(),
        "tickets_count": len(tickets),
        "tickets_file_exists": os.path.exists(tickets_file)
    })

@app.route("/api/tickets", methods=["GET"])
def get_tickets():
    """API endpoint to get all tickets"""
    return jsonify({"tickets": tickets, "count": len(tickets)})

@app.errorhandler(404)
def not_found(error):
    return render_template("index.html"), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# Entry point for running the Flask app
if __name__ == "__main__":
    print("🚀 Starting APIhub Support Bot...")
    
    # Ensure required directories exist
    for directory in ['static', 'templates']:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Created {directory} directory")
    
    # Check file permissions
    print("🔍 Checking file permissions...")
    check_file_permissions()
    
    # Check Ollama on startup
    print("🔍 Checking Ollama service...")
    if check_ollama_service():
        print("✅ All systems ready!")
    else:
        print("⚠️ Warning: Ollama service not available. The bot will create tickets for all queries.")
    
    print("🌐 Server starting on http://localhost:5000")
    print("📊 Dashboard available at http://localhost:5000/dashboard")
    print("🧪 Test ticket creation at http://localhost:5000/test-ticket")
    print("🔍 Debug tickets at http://localhost:5000/debug-tickets")
    
    app.run(debug=True, host="0.0.0.0", port=5000)