# Image Search Web UI - Quick Start Guide

## What Was Created

A complete, modern web interface for your Image Search application with the following features:

### Core Features

1. **Search Interface**
   - Natural language search with query enhancement (Gemini AI)
   - CLIP-based image retrieval with caption reranking
   - Configurable results (K parameter)
   - Pre-configured with optimal settings (alpha=0.4)

2. **Image Upload**
   - Drag-and-drop or button upload
   - Automatic indexing to Pinecone
   - Progress feedback
   - Batch upload support

3. **Search History**
   - Automatically saves all searches
   - Persistent in browser localStorage
   - Quick reload of previous searches
   - Shows query, results count, and timestamp

4. **Fixed-Size Collage Display**
   - Displays up to 8 images in a fixed-size rectangle
   - No scrolling needed to see initial results
   - Higher-ranked images appear larger
   - "See More" overlay for additional results
   - Hover to see captions and scores
   - Modern, responsive layout

5. **Settings Management**
   - Edit API keys (Pinecone, Gemini)
   - Configure model parameters
   - Test API connections
   - Persistent .env file updates

6. **Error Handling**
   - API validation on startup
   - Warning modals for configuration errors
   - Auto-redirect to settings
   - Clear error messages

## Directory Structure

```
web/
├── app.py                     # Flask backend API server
├── run.sh                     # Unix/Mac startup script
├── run.bat                    # Windows startup script
├── README.md                  # Detailed documentation
├── .gitignore                 # Git ignore rules
│
├── templates/                 # HTML templates
│   ├── index.html            # Main search interface
│   └── settings.html         # Configuration page
│
├── static/                    # Frontend assets
│   ├── css/
│   │   └── styles.css        # Modern dark theme
│   └── js/
│       ├── app.js            # Main application logic
│       └── settings.js       # Settings management
│
└── uploads/                   # Uploaded images storage
    └── .gitkeep
```

## How to Run

### Option 1: Using the Startup Script (Recommended)

**Mac/Linux:**
```bash
cd web
./run.sh
```

**Windows:**
```cmd
cd web
run.bat
```

### Option 2: Manual Start

```bash
# From project root
cd web
python app.py
```

Or:

```bash
# From project root
python web/app.py
```

### Option 3: Using Virtual Environment

```bash
# From project root
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
cd web
python app.py
```

The server will start at **http://localhost:5001**

## First Time Setup

1. **Install Flask** (if not already installed):
   ```bash
   pip install flask
   ```
   Or install all dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Keys**:

   Either edit `.env` in the project root:
   ```bash
   PINECONE_API_KEY=your_key_here
   GEMINI_API_KEY=your_key_here
   INDEX_NAME=img-search-clip-rp-384
   PINECONE_CLOUD=aws
   PINECONE_REGION=us-east-1
   CLIP_MODEL=sentence-transformers/clip-ViT-B-32
   GEMINI_MODEL=gemini-2.0-flash
   REDUCE_DIM=384
   ```

   Or use the Settings page in the web UI after starting the server.

3. **Start the Server**:
   ```bash
   cd web
   ./run.sh  # or run.bat on Windows
   ```

4. **Open Browser**:
   Navigate to http://localhost:5001

## Usage Workflow

### 1. Upload Images

- Click "Upload Images" or drag-and-drop images
- Supported formats: PNG, JPG, JPEG
- Images are copied to `web/uploads/` and indexed in Pinecone
- Wait for confirmation message

### 2. Search for Images

- Type a natural language query (e.g., "sunset on the beach")
- Optionally adjust K (number of results)
- Click Search or press Enter
- Wait for processing (query is enhanced, CLIP search, caption reranking)
- Results appear in asymmetric grid (larger = higher rank)

### 3. View Results

- Hover over images to see:
  - Similarity score
  - AI-generated caption
- Click to view full size (if implemented)
- Results auto-paginate (12 shown initially, click "Load More")

### 4. Manage Settings

- Click "Settings" in sidebar
- Edit configuration values
- Click "Test Connection" to validate
- Click "Save Settings" to persist
- **Restart server** for changes to take effect

## Technical Details

### Search Configuration

The UI uses optimal settings for the best results:

- **Mode**: CLIP with caption reranking
- **Alpha**: 0.4 (caption weight)
- **Query Enhancement**: Enabled (Gemini)
- **Expand Factor**: 3x (fetches 3×K for reranking)

### API Endpoints

- `GET /` - Main interface
- `GET /settings` - Settings page
- `POST /api/search` - Search images
- `POST /api/upload` - Upload files
- `GET/POST /api/settings` - Read/update config
- `GET /api/validate` - Validate API keys
- `GET /api/stats` - Index statistics
- `GET /api/image/<path>` - Serve images

### Data Flow

1. **Upload**: File → Flask → `web/uploads/` → Pinecone index
2. **Search**: Query → Enhancement (Gemini) → CLIP embedding → Pinecone → Caption reranking → Results
3. **Settings**: Form → Flask → `.env` file

## Troubleshooting

### Server won't start

**Check:**
- Flask is installed: `pip install flask`
- You're in the `web/` directory
- Port 5000 is available
- .env file exists in project root

### API Configuration Error on startup

**Solution:**
1. Check `.env` file has PINECONE_API_KEY and GEMINI_API_KEY
2. Or click "Go to Settings" and add them in the UI
3. Click "Test Connection" to validate

### No search results

**Check:**
1. Images are uploaded (check stats counter in sidebar)
2. Pinecone index exists and has vectors
3. Try a different, more general query

### Images not displaying

**Check:**
- Uploaded images are in `web/uploads/`
- For indexed images, original paths are accessible
- Browser console (F12) for errors

### Settings not saving

**Solution:**
1. Ensure you clicked "Save Settings"
2. **Restart the server** (required!)
3. Check `.env` file permissions

## Design Highlights

### Modern Dark Theme
- Custom CSS with modern gradients
- Responsive layout
- Smooth animations and transitions
- Mobile-friendly

### Fixed-Size Collage
- CSS Grid with 8 image slots in a fixed rectangle (~570px height)
- Top results span more columns/rows
- No scrolling needed to see initial results
- "See More" overlay shows count of remaining results
- Expands to scrollable grid when clicked
- Responsive breakpoints for smaller screens

### User Experience
- Real-time feedback (spinners, status messages)
- Persistent search history
- Drag-and-drop upload
- Keyboard shortcuts (Enter to search)
- Error modals with actionable buttons

## Next Steps

1. **Upload some test images** to build your index
2. **Try different search queries** to test the system
3. **Explore the settings** to customize configuration
4. **Check search history** to review past searches

## Support

For detailed documentation, see:
- `web/README.md` - Complete web UI documentation
- `README.md` - Main project documentation
- `QUICKSTART.md` - Backend CLI guide

## Security Note

This application is designed for **local use only**:
- Runs on localhost by default
- No authentication required
- API keys stored in .env file
- Uploaded files stored locally

**Do not expose to the internet without adding authentication!**

---

Enjoy your new Image Search Web UI!
