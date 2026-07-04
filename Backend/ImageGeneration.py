import asyncio
from io import BytesIO
from pathlib import Path
from random import randint
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image
from huggingface_hub import AsyncInferenceClient
from Backend.Config import ROOT_DIR, get_env, require_env
from time import sleep

DATA_DIR = ROOT_DIR / "Data"
REQUEST_FILE = ROOT_DIR / "Frontend" / "Files" / "ImageGeneration.data"
GENERATED_IMAGES_FILE = ROOT_DIR / "Frontend" / "Files" / "GeneratedImages.data"


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

def _image_stem(prompt: str) -> str:
    stem = re.sub(r'[<>:"/\\|?*]+', "", prompt.strip())
    stem = re.sub(r"\s+", "_", stem)
    return stem or "generated_image"


def publish_generated_images(image_paths):
    GENERATED_IMAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if GENERATED_IMAGES_FILE.exists():
        existing = GENERATED_IMAGES_FILE.read_text(encoding="utf-8").strip()

    pending_paths = [existing] if existing else []
    pending_paths.extend(str(path) for path in image_paths)
    GENERATED_IMAGES_FILE.write_text("\n".join(pending_paths), encoding="utf-8")

# Hugging Face Inference Providers image settings.
IMAGE_MODEL = get_env("HuggingFaceImageModel", "black-forest-labs/FLUX.1-schnell")
IMAGE_PROVIDER = get_env("HuggingFaceProvider", "auto")
IMAGE_TIMEOUT_SECONDS = _float_env("HuggingFaceImageTimeoutSeconds", 90)
IMAGES_PER_PROMPT = max(1, _int_env("HuggingFaceImagesPerPrompt", 1))


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
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tasks = []

    for _ in range(IMAGES_PER_PROMPT):
        payload = {
            "inputs": f"{prompt}, quality=4K, sharpness=maximum, Ultra High details, high resolution",
            "parameters": {
                "seed": randint(0, 1000000),
            },
        }
        tasks.append(asyncio.create_task(query(payload)))

    image_results = await asyncio.gather(*tasks, return_exceptions=True)
    saved_count = 0
    saved_paths = []
    errors = []

    for image_number, result in enumerate(image_results, start=1):
        if isinstance(result, Exception):
            errors.append(f"image {image_number}: {result}")
            print(f"Image {image_number} failed: {result}")
            continue

        image_path = DATA_DIR / f"{_image_stem(prompt)}{image_number}.jpg"
        with open(image_path, "wb") as f:
            f.write(result)
        saved_count += 1
        saved_paths.append(image_path)
        print(f"Saved image: {image_path}")

    if saved_count == 0:
        raise RuntimeError("All image generation requests failed. " + " | ".join(errors))

    if errors:
        print(f"{len(errors)} image request(s) failed, but {saved_count} image(s) were saved.")

    return saved_paths

# Wrapper function to generate images and publish them to the GUI
def GenerateImages(prompt: str):
    image_paths = asyncio.run(generate_images(prompt)) # Run the async image generation
    publish_generated_images(image_paths)

def monitor_image_generation_requests():
    while True:
        try:
            # Read the status and prompt from the data file
            with open(REQUEST_FILE, "r") as f:
                Data = str(f.read())
            
            Prompt, Status = Data.rsplit(",", 1)
            
            # If the status indicates an image generation request
            if Status == "True":
                print("Generating Images...")
                GenerateImages(prompt=Prompt)

                # Reset the status in the file after generating images
                with open(REQUEST_FILE, "w") as f:
                    f.write("False,False")

                return True # Exit the loop after processing the request

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
                REQUEST_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(REQUEST_FILE, "w") as f:
                    f.write("False,False")
            except Exception as reset_error:
                print(f"Could not reset image generation status: {reset_error}")
            return False


if __name__ == "__main__":
    raise SystemExit(0 if monitor_image_generation_requests() else 1)
