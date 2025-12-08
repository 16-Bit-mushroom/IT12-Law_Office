# serve.py
from waitress import serve
from app import create_app # Import your app factory

app = create_app()

if __name__ == "__main__":
    print("-------------------------------------------------------")
    print(" SYSTEM IS RUNNING. DO NOT CLOSE THIS WINDOW.")
    print(" Access on Server: http://localhost:8080")
    print(" Access on Clients: http://192.168.1.2:8080")
    print("-------------------------------------------------------")
    
    # threads=6 allows multiple users to process requests simultaneously
    serve(app, host='0.0.0.0', port=8080, threads=6)