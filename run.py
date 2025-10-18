import uvicorn
# Import the main app object directly
import app.main

if __name__ == "__main__":
    # Now, instead of passing a string, we pass the actual app object.
    # This makes the dependency clear to PyInstaller.
    uvicorn.run(app.main.app, host="127.0.0.1", port=8000, reload=False)