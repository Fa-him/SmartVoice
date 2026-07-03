import asyncio
from io import BytesIO
from random import randint
from PIL import Image
from huggingface_hub import AsyncInferenceClient
from Backend.Config import get_env, require_env
import os
from time import sleep


def _int_env(name: str, default: int) -> int:
    try:
        return int(get_env(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(get_env(name, str(default)))
    except (TypeError, ValueError):
        return default


# Function to open and display images based on a given prompt
def open_images(prompt):
    folder_path = r"Data" # Folder where the images are stored
    prompt = prompt.replace(" ", "_") # Replace spaces in prompt with underscores

    # Generate the filenames for the images
    Files = [f"{prompt}{i}.jpg" for i in range(1, IMAGES_PER_PROMPT + 1)]

    for jpg_file in Files:
        image_path = os.path.join(folder_path, jpg_file)

        try:
            # Try to open and display the image
            img = Image.open(image_path)
            print(f"Opening image: {image_path}")
            img.show()
            sleep(1) # Pause for 1 second before showing the next image

        except IOError:
            print(f"Unable to open {image_path}")

# Hugging Face Inference Providers image settings.
IMAGE_MODEL = get_env("HuggingFaceImageModel", "black-forest-labs/FLUX.1-schnell")
IMAGE_PROVIDER = get_env("HuggingFaceProvider", "auto")
IMAGE_TIMEOUT_SECONDS = _float_env("HuggingFaceImageTimeoutSeconds", 90)
IMAGES_PER_PROMPT = max(1, _int_env("HuggingFaceImagesPerPrompt", 4))


def _client() -> AsyncInferenceClient:
    provider = IMAGE_PROVIDER.strip() or None
    return AsyncInferenceClient(
        model=IMAGE_MODEL,
        provider=provider,
        token=require_env("HuggingFaceAPIKey"),
        timeout=IMAGE_TIMEOUT_SECONDS,
    )


def _image_to_jpeg_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def _payload_kwargs(payload: dict) -> dict:
    parameters = payload.get("parameters", {})
    if not isinstance(parameters, dict):
        return {}

    allowed = {
        "negative_prompt",
        "height",
        "width",
        "num_inference_steps",
        "guidance_scale",
        "scheduler",
        "seed",
        "extra_body",
    }
    return {key: parameters[key] for key in allowed if key in parameters}

# Async function to send a query to the Hugging Face API
async def query(payload: dict) -> bytes:
    prompt = payload.get("inputs", "").strip()
    if not prompt:
        raise ValueError("Image generation payload must include a non-empty 'inputs' prompt.")

    image = await _client().text_to_image(prompt, **_payload_kwargs(payload))
    return _image_to_jpeg_bytes(image)

# Async function to generate images based on the given prompt
async def generate_images(prompt: str):
    tasks = []
    
    # Create image generation tasks
    for _ in range(IMAGES_PER_PROMPT):
        payload = {
            "inputs": f"{prompt}, quality=4K, sharpness=maximum, Ultra High details, high resolution",
            "parameters": {
                "seed": randint(0, 1000000),
            },
        }
        task = asyncio.create_task(query(payload))
        tasks.append(task)
        
    # Wait for all tasks to complete
    image_bytes_list = await asyncio.gather(*tasks)
    
    # Save the generated images to files
    for i, image_bytes in enumerate(image_bytes_list):
        with open(fr"Data\{prompt.replace(' ', '_')}{i + 1}.jpg", "wb") as f:
            f.write(image_bytes)

# Wrapper function to generate and open images
def GenerateImages(prompt: str):
    asyncio.run(generate_images(prompt)) # Run the async image generation
    open_images(prompt) # Open the generated images

def monitor_image_generation_requests():
    while True:
        try:
            # Read the status and prompt from the data file
            with open(r"Frontend\Files\ImageGeneration.data", "r") as f:
                Data = str(f.read())
            
            Prompt, Status = Data.rsplit(",", 1)
            
            # If the status indicates an image generation request
            if Status == "True":
                print("Generating Images...")
                GenerateImages(prompt=Prompt)

                # Reset the status in the file after generating images
                with open(r"Frontend\Files\ImageGeneration.data", "w") as f:
                    f.write("False,False")

                break # Exit the loop after processing the request

            else:
                sleep(1) # Wait for 1 second before checking again

        except FileNotFoundError:
            sleep(1)
        except ValueError as e:
            print(f"Invalid image generation request: {e}")
            sleep(1)
        except Exception as e:
            print(f"Image generation failed: {e}")
            try:
                with open(r"Frontend\Files\ImageGeneration.data", "w") as f:
                    f.write("False,False")
            except Exception as reset_error:
                print(f"Could not reset image generation status: {reset_error}")
            break


if __name__ == "__main__":
    monitor_image_generation_requests()
