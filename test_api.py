import requests
from PIL import Image
import io
import os
from dotenv import load_dotenv  # Add this import

load_dotenv()


# Hugging Face API configuration
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
prompt = "Boy with Flower"
payload = {"inputs": prompt}

# Create directory for saving images if it doesn't exist
if not os.path.exists("static/images"):
    os.makedirs("static/images")

# Make the API request
try:
    response = requests.post(HF_API_URL, headers=headers, json=payload)
    print("Status Code:", response.status_code)

    if response.status_code == 200:
        print("Success! Image data received.")

        # Save image
        try:
            image = Image.open(io.BytesIO(response.content))
            # Create safe filename from prompt
            safe_prompt = prompt[:50].replace(' ', '_').replace('/', '_')
            image_path = f"static/images/generated_{safe_prompt}_{str(abs(hash(prompt)))[-8:]}.png"
            image.save(image_path)
            print(f"Image saved successfully at: {image_path}")

            # Show image (optional)
            image.show()

        except Exception as image_error:
            print("Failed to process/save image:", str(image_error))

    else:
        print("Failed to generate image. Response:", response.text)
        if response.status_code == 503:
            print("Model is loading. Please wait and try again.")
        elif response.status_code == 401:
            print("Invalid token. Please check your Hugging Face API token.")

except requests.exceptions.RequestException as e:
    print("Request failed:", str(e))
except Exception as e:
    print("An unexpected error occurred:", str(e))