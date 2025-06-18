from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
import os
from PIL import Image
import io
import time
import json
import logging
from dotenv import load_dotenv
import base64
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)

# Hugging Face API configuration
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# Updated model list with more reliable endpoints
MODELS = [
    {
        "name": "Stable Diffusion XL",
        "url": "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
        "timeout": 120,
        "max_retries": 2
    },
    {
        "name": "Stable Diffusion 2.1",
        "url": "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1",
        "timeout": 90,
        "max_retries": 2
    },
    {
        "name": "FLUX.1-dev",
        "url": "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev",
        "timeout": 150,
        "max_retries": 1
    },
    {
        "name": "Stable Diffusion 1.5",
        "url": "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5",
        "timeout": 60,
        "max_retries": 3
    },
    {
        "name": "Dreamlike Photoreal",
        "url": "https://api-inference.huggingface.co/models/dreamlike-art/dreamlike-photoreal-2.0",
        "timeout": 90,
        "max_retries": 2
    }
]

headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# Ensure the static/images directory exists
os.makedirs("static/images", exist_ok=True)


def check_model_status(model_url):
    """Check if a model endpoint is available with better error handling"""
    try:
        # First, try a simple GET request to check if endpoint exists
        response = requests.get(model_url, headers=headers, timeout=10)

        if response.status_code == 200:
            return True
        elif response.status_code == 503:
            # Model is loading but available
            return True
        elif response.status_code == 401:
            logger.warning(f"Authentication issue for {model_url}")
            return False
        elif response.status_code == 404:
            logger.warning(f"Model not found: {model_url}")
            return False
        else:
            # Try a small test request to verify the model actually works
            test_payload = {
                "inputs": "test",
                "parameters": {
                    "num_inference_steps": 1,
                    "width": 64,
                    "height": 64
                }
            }
            test_response = requests.post(
                model_url,
                headers=headers,
                json=test_payload,
                timeout=30
            )
            return test_response.status_code in [200, 503]

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout checking model status: {model_url}")
        return False
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error checking model status for {model_url}: {str(e)}")
        return False


def enhance_prompt(prompt):
    """Enhance the prompt for better image quality"""
    quality_terms = "high quality, detailed, masterpiece, best quality, sharp focus"
    if not any(term in prompt.lower() for term in ["quality", "detailed", "masterpiece"]):
        return f"{prompt}, {quality_terms}"
    return prompt


def generate_with_model(model, prompt, max_retries=None):
    """Try to generate an image with a specific model with improved error handling"""
    if max_retries is None:
        max_retries = model.get("max_retries", 2)

    enhanced_prompt = enhance_prompt(prompt)
    logger.info(f"Trying {model['name']} for prompt: {enhanced_prompt[:100]}...")

    for attempt in range(max_retries):
        try:
            # Prepare the payload with optimized parameters
            payload = {
                "inputs": enhanced_prompt,
                "parameters": {
                    "guidance_scale": 7.5,
                    "num_inference_steps": 30,  # Reduced for faster generation
                    "width": 1024,
                    "height": 1024
                },
                "options": {
                    "wait_for_model": True,
                    "use_cache": False
                }
            }

            logger.info(f"Attempt {attempt + 1}/{max_retries} with {model['name']}")

            response = requests.post(
                model["url"],
                headers=headers,
                json=payload,
                timeout=model["timeout"]
            )

            logger.info(f"Response status: {response.status_code}")

            if response.status_code == 200:
                try:
                    # Check if response is valid image data
                    if len(response.content) < 1000:  # Too small to be a valid image
                        logger.error(f"Response too small from {model['name']}: {len(response.content)} bytes")
                        continue

                    # Try to open and validate the image
                    image = Image.open(io.BytesIO(response.content))

                    # Verify image dimensions
                    if image.size[0] < 64 or image.size[1] < 64:
                        logger.error(f"Generated image too small: {image.size}")
                        continue

                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    model_safe_name = model['name'].lower().replace(' ', '_').replace('.', '_')
                    filename = f"{model_safe_name}_{timestamp}.png"
                    image_path = os.path.join("static/images", filename)

                    # Save image
                    image.save(image_path, "PNG", optimize=True)

                    logger.info(f"Successfully generated image with {model['name']}: {filename}")
                    return {
                        "success": True,
                        "image_url": f"/static/images/{filename}",
                        "model": model['name'],
                        "filename": filename,
                        "image_size": image.size,
                        "file_size": len(response.content)
                    }
                except Exception as img_error:
                    logger.error(f"Error processing image from {model['name']}: {str(img_error)}")
                    # Log response content type and size for debugging
                    logger.error(f"Response content-type: {response.headers.get('content-type')}")
                    logger.error(f"Response size: {len(response.content)} bytes")
                    continue

            elif response.status_code == 503:
                # Model is loading
                try:
                    resp_data = response.json()
                    wait_time = min(resp_data.get("estimated_time", 20), 120)  # Cap at 2 minutes
                    logger.info(f"{model['name']} is loading, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                except:
                    wait_time = min(20 + (attempt * 10), 60)  # Progressive wait time
                    logger.info(f"{model['name']} is loading, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue

            elif response.status_code == 400:
                logger.error(f"{model['name']} returned 400 (Bad Request): {response.text}")
                return {"success": False, "error": f"Bad request for {model['name']}: Invalid prompt or parameters"}

            elif response.status_code == 401:
                logger.error(f"{model['name']} returned 401 (Unauthorized)")
                return {"success": False, "error": f"Authentication failed for {model['name']}"}

            elif response.status_code == 404:
                logger.error(f"{model['name']} endpoint not found")
                return {"success": False, "error": f"Model {model['name']} not found"}

            elif response.status_code == 429:
                # Rate limited
                wait_time = 60 + (attempt * 30)  # Progressive backoff
                logger.warning(f"{model['name']} rate limited, waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue

            else:
                logger.error(f"{model['name']} returned {response.status_code}: {response.text}")
                if attempt < max_retries - 1:
                    time.sleep(15 * (attempt + 1))  # Progressive backoff
                    continue
                break

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for {model['name']} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(20)
                continue
            break

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {model['name']}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(15)
                continue
            break

    return {"success": False, "error": f"Failed to generate with {model['name']} after {max_retries} attempts"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/models/status")
def check_models():
    """Check status of all available models with detailed information"""
    model_status = []
    for model in MODELS:
        logger.info(f"Checking status for {model['name']}...")
        status = check_model_status(model["url"])
        model_status.append({
            "name": model["name"],
            "available": status,
            "url": model["url"],
            "timeout": model["timeout"]
        })
        logger.info(f"{model['name']}: {'✅ Available' if status else '❌ Unavailable'}")

    return jsonify({
        "models": model_status,
        "total_models": len(MODELS),
        "available_models": sum(1 for m in model_status if m["available"]),
        "api_token_configured": bool(HF_API_TOKEN)
    })


@app.route("/generate", methods=["POST"])
def generate_image():
    prompt = request.form.get("prompt")
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    if not HF_API_TOKEN:
        return jsonify({"error": "Hugging Face API token not configured"}), 500

    if len(prompt.strip()) < 3:
        return jsonify({"error": "Prompt too short. Please provide a more descriptive prompt."}), 400

    logger.info(f"Starting image generation for prompt: {prompt[:100]}...")

    # Try each model until one works
    last_errors = []

    for i, model in enumerate(MODELS):
        logger.info(f"Attempting generation with {model['name']} ({i + 1}/{len(MODELS)})")

        result = generate_with_model(model, prompt)

        if result["success"]:
            logger.info(f"✅ Successfully generated image with {model['name']}")
            return jsonify({
                "image_url": result["image_url"],
                "model": result["model"],
                "prompt": prompt,
                "filename": result["filename"],
                "image_size": result.get("image_size"),
                "file_size": result.get("file_size"),
                "attempts": i + 1
            })
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.warning(f"❌ Failed with {model['name']}: {error_msg}")
            last_errors.append(f"{model['name']}: {error_msg}")
            continue

    # If all models failed
    logger.error("All models failed to generate image")
    return jsonify({
        "error": "All image generation models are currently unavailable or failed to generate the image.",
        "details": "This may be due to high demand, temporary service issues, or API quota limits.",
        "model_errors": last_errors,
        "suggestion": "Please try again in a few minutes, or try a different prompt."
    }), 503


@app.route("/generate/<model_name>", methods=["POST"])
def generate_with_specific_model(model_name):
    """Generate with a specific model"""
    prompt = request.form.get("prompt")
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    # Find the requested model
    selected_model = None
    for model in MODELS:
        if model["name"].lower().replace(" ", "_").replace(".", "_") == model_name.lower():
            selected_model = model
            break

    if not selected_model:
        available_models = [m["name"] for m in MODELS]
        return jsonify({
            "error": f"Model '{model_name}' not found",
            "available_models": available_models
        }), 404

    result = generate_with_model(selected_model, prompt)

    if result["success"]:
        return jsonify({
            "image_url": result["image_url"],
            "model": result["model"],
            "prompt": prompt,
            "filename": result["filename"],
            "image_size": result.get("image_size"),
            "file_size": result.get("file_size")
        })
    else:
        return jsonify({
            "error": f"Failed to generate with {selected_model['name']}",
            "details": result.get("error", "Unknown error")
        }), 500


@app.route("/static/images/<filename>")
def serve_image(filename):
    return send_from_directory("static/images", filename)


@app.route("/health")
def health_check():
    """Comprehensive health check endpoint"""
    api_configured = bool(HF_API_TOKEN)

    # Quick model availability check
    available_models = 0
    if api_configured:
        for model in MODELS[:2]:  # Check first 2 models for speed
            if check_model_status(model["url"]):
                available_models += 1

    status = "healthy" if api_configured and available_models > 0 else "degraded"

    return jsonify({
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "models_total": len(MODELS),
        "models_checked": 2,
        "models_available": available_models,
        "api_token_configured": api_configured,
        "static_directory_exists": os.path.exists("static/images")
    })


@app.route("/debug/test-token")
def test_token():
    """Debug endpoint to test API token (remove in production)"""
    if not HF_API_TOKEN:
        return jsonify({"error": "No API token configured"}), 500

    # Test with a simple API call
    test_url = "https://api-inference.huggingface.co/models/bert-base-uncased"
    try:
        response = requests.get(test_url, headers=headers, timeout=10)
        return jsonify({
            "token_valid": response.status_code != 401,
            "status_code": response.status_code,
            "token_length": len(HF_API_TOKEN) if HF_API_TOKEN else 0
        })
    except Exception as e:
        return jsonify({
            "error": f"Token test failed: {str(e)}",
            "token_configured": bool(HF_API_TOKEN)
        })


if __name__ == "__main__":
    if not HF_API_TOKEN:
        logger.error("❌ Missing HF_API_TOKEN in environment variables!")
        logger.info("Please set your Hugging Face API token in a .env file:")
        logger.info("HF_API_TOKEN=your_token_here")
        logger.info("You can get a free token at: https://huggingface.co/settings/tokens")
        exit(1)

    logger.info("🚀 Starting Flask app with improved model fallbacks...")
    logger.info(f"📊 Available models: {len(MODELS)}")

    # Check all models on startup
    for model in MODELS:
        status = "✅" if check_model_status(model["url"]) else "❌"
        logger.info(f"{status} {model['name']}")

    app.run(
        debug=os.getenv("DEBUG", "false").lower() == "true",
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000))
    )