# 🎨 Midjourney v3 Studio

A professional, dark-themed SaaS-style GUI dashboard for the Midjourney v3 API (UseAPI provider).

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

### 🎨 Creation (Imagine)
- Full text-to-image generation with all Midjourney parameters
- Aspect ratio, version, stylize, chaos, quality, weird controls
- Video generation support with motion/loop options
- Style reference (--sref) and character reference (--cref)
- Seed control for reproducible results
- Quick templates for common styles
- Real-time job polling with progress tracking

### 🔀 Fusion (Blend)
- Drag-and-drop interface for 2-5 images
- **Local file uploads using `multipart/form-data` with `imageBlob` keys**
- Portrait/Square/Landscape dimension options
- Visual preview before blending

### 🔍 Analysis (Describe)
- Upload images for reverse prompt engineering
- **Local file upload using `imageBlob` parameter**
- Returns 4 AI-generated prompt suggestions
- One-click copy or use prompts directly

### 🎛️ Button Actions
- U1-U4 (Upscale individual quadrants)
- V1-V4 (Variations)
- Vary (Strong/Subtle/Region)
- Zoom Out 1.5x/2x, Custom Zoom
- Pan (⬅️➡️⬆️⬇️)
- Reroll (🔄)
- Upscale quality options (2x/4x/Subtle/Creative)
- Video animation controls

### ⚙️ Settings Management
- View/modify Midjourney settings
- Toggle speed modes (Turbo/Fast/Relax)
- Toggle Remix and Variability modes
- Account info display

### 📊 Job Monitor
- Real-time running job display
- Job history with quick access
- Cancel running jobs
- Detailed job inspection

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- UseAPI.net API token ([Get one here](https://useapi.net))
- Discord token configured for Midjourney

### Installation

```bash
# Clone or download the project
cd midjourney-studio

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy the secrets template:
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

2. Edit `.streamlit/secrets.toml` with your credentials:
```toml
api_token = "your-useapi-token"
discord_token = "your-discord-token"
```

### Run the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## 📁 Project Structure

```
midjourney-studio/
├── app.py                    # Main application
├── requirements.txt          # Python dependencies
├── .streamlit/
│   ├── config.toml          # Streamlit theme configuration
│   └── secrets.toml         # API credentials (create from .example)
└── README.md
```

## 📚 API Documentation References

This application is built against the Midjourney v3 API documentation:

| Feature | Documentation File |
|---------|-------------------|
| Imagine | `post-midjourney-jobs-imagine.md` |
| Blend | `post-midjourney-jobs-blend.md` |
| Describe | `post-midjourney-jobs-describe.md` |
| Button Actions | `post-midjourney-jobs-button.md` |
| Seed Extraction | `post-midjourney-jobs-seed.md` |
| Job Status | `get-midjourney-jobs-jobid.md` |
| Running Jobs | `get-midjourney-jobs.md` |
| Settings | `post-midjourney-jobs-settings.md` |
| Speed Modes | `post-midjourney-jobs-fast/relax/turbo.md` |
| Account Config | `post-midjourney-accounts.md` |

## 🔑 Key Implementation Details

### File Uploads (Critical!)

The application uses `multipart/form-data` with `imageBlob` parameters for file uploads:

```python
# Blend endpoint - uses imageBlob_1, imageBlob_2, etc.
form_data = {
    "imageBlob_1": (filename, file_bytes, content_type),
    "imageBlob_2": (filename, file_bytes, content_type),
    "blendDimensions": (None, "Square"),
    "stream": (None, "false")
}
response = requests.post(url, headers=headers, files=form_data)

# Describe endpoint - uses single imageBlob
form_data = {
    "imageBlob": (filename, file_bytes, content_type),
    "stream": (None, "false")
}
response = requests.post(url, headers=headers, files=form_data)
```

### Prompt Construction

Parameters are programmatically concatenated into the final prompt:

```python
# Base prompt + parameters
"A dragon --ar 16:9 --v 7 --s 250 --c 20 --q 1"
```

### Job Polling

Non-blocking polling with 3-second intervals:

```python
while status not in ["completed", "failed", "moderated"]:
    status_code, job_data = api.get_job(job_id)
    # Update UI...
    time.sleep(3)
```

## 🎯 Usage Tips

1. **Start with Settings**: Configure your Discord channel in the Settings tab first
2. **Check Channel Status**: Use the sidebar to verify your channel is properly configured
3. **Use Templates**: Quick templates in the Creation tab help you get started faster
4. **Monitor Jobs**: Use the Job Monitor tab to track all your active and completed jobs
5. **Save Credentials**: Click "Save" in the sidebar to persist your API token

## ⚠️ Important Notes

- **Rate Limits**: The API has rate limits. If you get a 429 error, wait 10-30 seconds
- **Job Capacity**: Respect your Midjourney subscription's concurrent job limits
- **Moderation**: If you get a 596 error, check your Discord for moderation messages
- **File Size**: Maximum 10MB per image for blend/describe operations

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Check your API token is valid |
| 402 Payment Required | Check your UseAPI subscription |
| 429 Too Many Requests | Wait and retry, reduce concurrent jobs |
| 596 Pending Moderation | Log into Discord, resolve moderation/CAPTCHA, then reset channel |
| Channel Error | Use "Reset Channel" button in Settings |

## 📄 License

MIT License - Feel free to use and modify for your projects.

## 🙏 Credits

- [UseAPI.net](https://useapi.net) - Midjourney API provider
- [Streamlit](https://streamlit.io) - Application framework
- [Midjourney](https://midjourney.com) - AI image generation
