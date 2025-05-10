from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
import os
from PIL import Image
import io
import time
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Hugging Face API configuration
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
# Change to the model that's working in your test_api
HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# Ensure the static/images directory exists
os.makedirs("static/images", exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate_image():
    prompt = request.form.get("prompt")
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    try:
        # Try the API call up to 3 times if model is loading
        for attempt in range(3):
            print(f"Attempt {attempt + 1}: Sending request to Hugging Face API")
            try:
                # Increased timeout to 60 seconds to prevent timeouts
                response = requests.post(
                    HF_API_URL,
                    headers=headers,
                    json={"inputs": prompt},
                    timeout=60  # Increased from 30 to 60
                )

                print(f"Status code: {response.status_code}")

                if response.status_code == 200:
                    try:
                        # Save the image with a unique filename
                        image = Image.open(io.BytesIO(response.content))
                        filename = f"generated_{int(time.time())}.png"
                        image_path = os.path.join("static/images", filename)
                        image.save(image_path)
                        print(f"Image saved to {image_path}")
                        return jsonify({"image_url": f"/static/images/{filename}"})
                    except Exception as img_error:
                        print(f"Error processing image: {str(img_error)}")
                        return jsonify({"error": f"Error processing image: {str(img_error)}"}), 500

                # If model is still loading, parse the response and get estimated time
                elif response.status_code == 503 and attempt < 2:
                    try:
                        resp_data = response.json()
                        wait_time = resp_data.get("estimated_time", 10)
                        print(f"Model is loading, waiting {wait_time} seconds to retry...")
                        time.sleep(wait_time)
                        continue
                    except (json.JSONDecodeError, KeyError):
                        # Default wait time if we can't parse the response
                        print("Model is loading, waiting 10 seconds to retry...")
                        time.sleep(10)
                        continue
                else:
                    print(f"API Error: {response.text}")
                    return jsonify({
                        "error": f"API Error: {response.text}",
                        "status_code": response.status_code
                    }), response.status_code

            except requests.exceptions.Timeout:
                if attempt < 2:
                    wait_time = 15 * (attempt + 1)  # Progressive backoff
                    print(f"Request timed out. Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                    continue
                else:
                    return jsonify({"error": "The request to the API timed out after multiple attempts. The model might be under heavy load."}), 504
            except requests.exceptions.RequestException as req_err:
                print(f"Request error on attempt {attempt + 1}: {str(req_err)}")
                if attempt < 2:
                    time.sleep(10)
                    continue
                return jsonify({"error": f"Request failed: {str(req_err)}"}), 500

        # If we've exhausted all attempts
        return jsonify({"error": "Failed to generate image after multiple attempts"}), 500

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/static/images/<filename>")
def serve_image(filename):
    return send_from_directory("static/images", filename)


if __name__ == "__main__":
    print(f"Starting Flask app with API Token {'valid' if HF_API_TOKEN else 'missing'}")
    # For production, set debug to False
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))