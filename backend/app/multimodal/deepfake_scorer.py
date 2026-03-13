# backend/app/multimodal/deepfake_scorer.py
#
# Deepfake detection using a pretrained EfficientNet-B4 fine-tuned on
# FaceForensics++ (FF++) dataset.
#
# Model weights source: https://github.com/ondyari/FaceForensics
# We use the publicly available weights trained on FF++ (c23 compression).
#
# REQUIREMENTS (add to backend/requirements.txt):
#   torch==2.2.0
#   torchvision==0.17.0
#   facenet-pytorch==2.5.3      # MTCNN face detector
#   av==12.0.0                  # PyAV for video frame extraction
#   httpx==0.27.0
#   Pillow>=10.0.0
#   numpy>=1.24.0
#
# GPU is strongly recommended (CUDA). Falls back to CPU but is slow (~8s/frame).
# For CPU-only deployments, set MAX_FRAMES=4 in .env to keep latency under 30s.
#
# .env variables:
#   DEEPFAKE_WEIGHTS_PATH=/models/ff_efficientb4.pth   # path to local weights
#   DEEPFAKE_WEIGHTS_URL=https://...                    # optional: auto-download on first run
#   DEEPFAKE_MAX_FRAMES=16                              # frames sampled per video
#   DEEPFAKE_FACE_MARGIN=0.3                            # MTCNN face crop margin
#   DEEPFAKE_CONFIDENCE_THRESHOLD=0.65                 # score above this = flagged
#   DEEPFAKE_DEVICE=cuda                               # cuda | cpu | mps

import os
import asyncio
import hashlib
import tempfile
from pathlib import Path
from typing import Optional

import httpx
import numpy as np
from PIL import Image

# ── Lazy imports (only loaded when scorer is first called) ────────────────────
_model    = None
_detector = None
_device   = None
_transform = None


def _load_model():
    """Load MTCNN face detector + EfficientNet-B4 FF++ weights. Called once."""
    global _model, _detector, _device, _transform

    import torch
    import torchvision.transforms as T
    from facenet_pytorch import MTCNN
    from torchvision.models import efficientnet_b4, EfficientNet_B4_Weights

    device_str = os.getenv("DEEPFAKE_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
    if device_str == "mps" and not torch.backends.mps.is_available():
        device_str = "cpu"
    _device = torch.device(device_str)

    # Face detector (MTCNN)
    _detector = MTCNN(
        image_size=224,
        margin=float(os.getenv("DEEPFAKE_FACE_MARGIN", "0.3")),
        keep_all=True,
        device=_device,
        post_process=False,
        select_largest=False,
    )

    # EfficientNet-B4 backbone
    _model = efficientnet_b4(weights=None)
    # Replace classifier head: 1792 → 512 → 1 (binary: real/fake)
    import torch.nn as nn
    _model.classifier = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(1792, 512),
        nn.ReLU(),
        nn.Dropout(p=0.2),
        nn.Linear(512, 1),
    )

    # Load pretrained FF++ weights
    weights_path = os.getenv("DEEPFAKE_WEIGHTS_PATH", "/models/ff_efficientb4.pth")
    if not Path(weights_path).exists():
        _download_weights(weights_path)

    checkpoint = torch.load(weights_path, map_location=_device)
    # Handle both raw state_dict and wrapped checkpoints
    state_dict = checkpoint.get("model_state_dict", checkpoint.get("state_dict", checkpoint))
    _model.load_state_dict(state_dict, strict=False)
    _model.to(_device)
    _model.eval()

    # ImageNet normalization (FF++ weights trained with standard normalization)
    _transform = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    print(f"[deepfake_scorer] Model loaded on {_device}")


def _download_weights(dest_path: str):
    """Auto-download weights if DEEPFAKE_WEIGHTS_URL is set."""
    url = os.getenv("DEEPFAKE_WEIGHTS_URL", "")
    if not url:
        raise FileNotFoundError(
            f"Deepfake model weights not found at {dest_path}. "
            "Set DEEPFAKE_WEIGHTS_URL in .env for auto-download, "
            "or download manually from https://github.com/ondyari/FaceForensics"
        )
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    print(f"[deepfake_scorer] Downloading weights from {url} ...")
    import urllib.request
    urllib.request.urlretrieve(url, dest_path)
    print(f"[deepfake_scorer] Weights saved to {dest_path}")


# ── Video frame extraction ────────────────────────────────────────────────────

def _extract_frames(video_path: str, n_frames: int) -> list[Image.Image]:
    """
    Extract n_frames evenly spaced frames from a video file using PyAV.
    Returns list of PIL Images.
    """
    import av
    frames = []
    container = av.open(video_path)
    stream    = container.streams.video[0]
    total     = stream.frames or 300  # fallback if unknown

    # Evenly spaced indices
    indices = set(np.linspace(0, max(total - 1, 1), n_frames, dtype=int).tolist())

    for i, frame in enumerate(container.decode(stream)):
        if i in indices:
            frames.append(frame.to_image())  # PIL Image
        if len(frames) >= n_frames:
            break

    container.close()
    return frames


# ── Face crop extraction ──────────────────────────────────────────────────────

def _crop_faces(frames: list[Image.Image]) -> list[Image.Image]:
    """
    Run MTCNN on each frame, return all face crops.
    Falls back to full frame if no face detected (handles obscured faces).
    """
    import torch
    face_crops = []
    for frame in frames:
        try:
            # MTCNN returns tensor crops or None
            crops = _detector(frame)
            if crops is None:
                # No face found — use centre crop of full frame as fallback
                w, h = frame.size
                margin = min(w, h) // 6
                face_crops.append(frame.crop((margin, margin, w - margin, h - margin)))
                continue
            # crops shape: (N, C, H, W) tensor
            if crops.dim() == 3:
                crops = crops.unsqueeze(0)
            for crop_tensor in crops:
                # Convert tensor → PIL for transform pipeline
                arr = crop_tensor.permute(1, 2, 0).cpu().numpy()
                arr = np.clip(arr, 0, 255).astype(np.uint8)
                face_crops.append(Image.fromarray(arr))
        except Exception:
            face_crops.append(frame)

    return face_crops if face_crops else frames


# ── Inference ─────────────────────────────────────────────────────────────────

def _run_inference(face_crops: list[Image.Image]) -> dict:
    """
    Run EfficientNet-B4 on all face crops.
    Returns:
        score      : float 0-1  (1 = almost certainly deepfake)
        frame_scores: list[float] per-crop scores
        face_count : int
    """
    import torch
    if not face_crops:
        return {"score": 0.0, "frame_scores": [], "face_count": 0}

    tensors = torch.stack([_transform(c) for c in face_crops]).to(_device)

    with torch.no_grad():
        logits = _model(tensors).squeeze(1)          # (N,)
        probs  = torch.sigmoid(logits).cpu().numpy()  # (N,) in [0,1]

    frame_scores = [round(float(p), 4) for p in probs]

    # Aggregate: use 90th percentile (robust to a few false positives)
    score = float(np.percentile(probs, 90)) if len(probs) > 1 else float(probs[0])

    return {
        "score":        round(score, 4),
        "frame_scores": frame_scores,
        "face_count":   len(face_crops),
    }


# ── Public API ────────────────────────────────────────────────────────────────

async def score_video_url(media_url: str) -> dict:
    """
    Main entry point. Downloads video, extracts frames, scores for deepfake.

    Returns:
        deepfake_score  : float 0-1
        is_flagged      : bool  (score > CONFIDENCE_THRESHOLD)
        face_count      : int
        frames_analysed : int
        frame_scores    : list[float]
        model           : str
        error           : str | None
    """
    global _model

    # Lazy-load model on first call
    if _model is None:
        await asyncio.get_event_loop().run_in_executor(None, _load_model)

    max_frames  = int(os.getenv("DEEPFAKE_MAX_FRAMES", "16"))
    threshold   = float(os.getenv("DEEPFAKE_CONFIDENCE_THRESHOLD", "0.65"))

    # Download video to temp file
    tmp_path = None
    try:
        tmp_path = await _download_video(media_url)
        if not tmp_path:
            return _error_result("Failed to download video")

        # Frame extraction + face detection run in executor (blocking)
        frames = await asyncio.get_event_loop().run_in_executor(
            None, _extract_frames, tmp_path, max_frames
        )
        if not frames:
            return _error_result("No frames extracted from video")

        face_crops = await asyncio.get_event_loop().run_in_executor(
            None, _crop_faces, frames
        )

        result = await asyncio.get_event_loop().run_in_executor(
            None, _run_inference, face_crops
        )

        return {
            "deepfake_score":   result["score"],
            "is_flagged":       result["score"] >= threshold,
            "face_count":       result["face_count"],
            "frames_analysed":  len(frames),
            "frame_scores":     result["frame_scores"],
            "model":            "efficientnet_b4_ff++",
            "error":            None,
        }

    except Exception as e:
        return _error_result(str(e))

    finally:
        if tmp_path and Path(tmp_path).exists():
            Path(tmp_path).unlink(missing_ok=True)


async def score_image_url(media_url: str) -> dict:
    """
    Image deepfake scorer (GAN-generated face detection).
    Uses the same EfficientNet-B4 model — single image inference.
    """
    global _model
    if _model is None:
        await asyncio.get_event_loop().run_in_executor(None, _load_model)

    threshold = float(os.getenv("DEEPFAKE_CONFIDENCE_THRESHOLD", "0.65"))

    try:
        async with httpx.AsyncClient(timeout=15) as h:
            r = await h.get(media_url, follow_redirects=True)
            r.raise_for_status()
            img = Image.open(r).convert("RGB")

        face_crops = await asyncio.get_event_loop().run_in_executor(
            None, _crop_faces, [img]
        )
        result = await asyncio.get_event_loop().run_in_executor(
            None, _run_inference, face_crops
        )

        return {
            "deepfake_score": result["score"],
            "is_flagged":     result["score"] >= threshold,
            "face_count":     result["face_count"],
            "frames_analysed": 1,
            "frame_scores":   result["frame_scores"],
            "model":          "efficientnet_b4_ff++",
            "error":          None,
        }
    except Exception as e:
        return _error_result(str(e))


async def _download_video(url: str) -> Optional[str]:
    """Download video to a temp file, return path. Max 200MB."""
    MAX_BYTES = int(os.getenv("DEEPFAKE_MAX_VIDEO_MB", "200")) * 1024 * 1024
    suffix    = Path(url.split("?")[0]).suffix or ".mp4"
    tmp       = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as h:
            async with h.stream("GET", url) as r:
                r.raise_for_status()
                total = 0
                async for chunk in r.aiter_bytes(chunk_size=65536):
                    total += len(chunk)
                    if total > MAX_BYTES:
                        tmp.close()
                        Path(tmp.name).unlink(missing_ok=True)
                        return None
                    tmp.write(chunk)
        tmp.close()
        return tmp.name
    except Exception:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        return None


def _error_result(msg: str) -> dict:
    return {
        "deepfake_score":   0.0,
        "is_flagged":       False,
        "face_count":       0,
        "frames_analysed":  0,
        "frame_scores":     [],
        "model":            "efficientnet_b4_ff++",
        "error":            msg,
    }
